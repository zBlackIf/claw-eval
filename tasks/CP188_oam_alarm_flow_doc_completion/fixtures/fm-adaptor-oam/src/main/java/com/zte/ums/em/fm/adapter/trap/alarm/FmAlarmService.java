package com.zte.ums.em.fm.adapter.trap.alarm;

import com.zte.ums.em.fm.adapter.alarm.AlarmDelegate;
import com.zte.ums.em.fm.adapter.alarm.entity.SnmpAlarmData;
import com.zte.ums.em.fm.adapter.common.FmConsts;
import com.zte.ums.em.fm.adapter.common.FmException;
import com.zte.ums.em.fm.adapter.trap.entity.OamTrapEntity;
import com.zte.ums.em.fm.adapter.trap.entity.DelayClearAlarm;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import java.util.Map;
import java.util.concurrent.ConcurrentHashMap;
import java.util.concurrent.DelayQueue;

/**
 * FmAlarmService - Alarm processing service with OAM trap ordering.
 * Handles both regular alarms and OAM-specific trap reordering.
 */
public class FmAlarmService {

    private static final Logger LOG = LoggerFactory.getLogger(FmAlarmService.class);

    /** Per-NE OAM trap state tracking */
    private static final Map<String, OamTrapEntity> oamTrapMap = new ConcurrentHashMap<>();

    /** Delay queue for out-of-order clear alarms */
    private static final DelayQueue<DelayClearAlarm> delayClearQueue = new DelayQueue<>();

    /** Maximum allowed trap ID jump before considering it a reset */
    private static final int MAX_JUMP_THRESHOLD = 100;

    /** Delay time in ms for out-of-order clear alarms */
    private static final long CLEAR_DELAY_MS = 30000;

    /**
     * Main alarm processing entry point.
     * Routes between notification (direct) and event (per-NE thread) processing.
     *
     * @param data parsed alarm data from receiveTrap()
     */
    public void alarmProcess(SnmpAlarmData data) {
        if (data.isNotification()) {
            // Notification alarms: direct processing, no ordering needed
            processNotification(data);
        } else if (isOamTrapAlarm(data)) {
            // OAM trap alarms: apply ordering logic
            processOamTrapAlarm(data);
        } else {
            // Regular event alarms: delegate directly
            processRegularAlarm(data);
        }
    }

    /**
     * Determines if the alarm originated from an OAM network element.
     * OAM NEs have sendNotificationId field set and neType starts with "OAM-".
     */
    private boolean isOamTrapAlarm(SnmpAlarmData data) {
        return data.getSendNotificationId() != null
                && data.getNeType() != null
                && data.getNeType().startsWith("OAM-");
    }

    /**
     * Processes OAM trap alarms with ordering guarantee.
     *
     * Algorithm:
     * 1. Get or create OamTrapEntity for this NE (keyed by workId = neName + neType)
     * 2. Extract currentTrapId from sendNotificationId
     * 3. Compare currentTrapId with expectedId:
     *    a) currentTrapId == expectedId: normal order, process immediately
     *    b) currentTrapId > expectedId: out-of-order (gap detected)
     *       - Update expectedId to currentTrapId + 1
     *       - If alarm type is CLEAR and currentTrapId <= maxJumpId:
     *         put into delay queue (wait for missing RAISE to arrive)
     *       - Otherwise: process immediately (skip gap)
     *    c) currentTrapId < expectedId: late arrival of previously skipped trap
     *       - If gap < MAX_JUMP_THRESHOLD: process immediately (late but valid)
     *       - If gap >= MAX_JUMP_THRESHOLD: treat as NE restart, reset state
     *
     * @param data the OAM alarm data with sendNotificationId
     */
    public void processOamTrapAlarm(SnmpAlarmData data) {
        String workId = data.getNeName() + "_" + data.getNeType();
        int currentTrapId = Integer.parseInt(data.getSendNotificationId());

        OamTrapEntity trapEntity = oamTrapMap.computeIfAbsent(workId,
                k -> new OamTrapEntity(workId, 1));

        int expectedId = trapEntity.getExpectedId();
        String type = data.getType();

        LOG.debug("OAM trap: workId={}, currentId={}, expectedId={}, type={}",
                workId, currentTrapId, expectedId, type);

        if (currentTrapId == expectedId) {
            // Normal order: process and advance
            trapEntity.setExpectedId(currentTrapId + 1);
            delegateAlarm(data, workId, expectedId);

        } else if (currentTrapId > expectedId) {
            // Out-of-order: gap detected
            LOG.warn("OAM trap gap: expected={}, got={}, workId={}",
                    expectedId, currentTrapId, workId);

            trapEntity.setExpectedId(currentTrapId + 1);
            trapEntity.setMaxJumpId(Math.max(trapEntity.getMaxJumpId(), currentTrapId));
            trapEntity.incrementJumpCount();

            if (FmConsts.TABLE_ALARMCLEARED.equalsIgnoreCase(type)
                    && currentTrapId <= trapEntity.getMaxJumpId()) {
                // Clear alarm arrived before its Raise - put in delay queue
                addToDelayQueue(data, workId, expectedId);
            } else {
                // Non-clear or beyond max jump - process immediately
                delegateAlarm(data, workId, expectedId);
            }

        } else {
            // currentTrapId < expectedId: late arrival
            int gap = expectedId - currentTrapId;
            if (gap >= MAX_JUMP_THRESHOLD) {
                // Likely NE restart - reset state
                LOG.info("OAM trap NE restart detected: workId={}, resetting state", workId);
                trapEntity.reset(currentTrapId + 1);
            }
            // Process the late alarm regardless
            delegateAlarm(data, workId, expectedId);
        }
    }

    /**
     * Adds a clear alarm to the delay queue, waiting for its corresponding raise.
     */
    private void addToDelayQueue(SnmpAlarmData data, String workId, int expectedId) {
        DelayClearAlarm delayed = new DelayClearAlarm(data, workId, expectedId,
                System.currentTimeMillis() + CLEAR_DELAY_MS);
        delayClearQueue.put(delayed);
        LOG.info("Clear alarm queued: alarmId={}, workId={}, delay={}ms",
                data.getAlarmId(), workId, CLEAR_DELAY_MS);
    }

    /**
     * Delegates the alarm to AlarmDelegate for final processing.
     */
    private void delegateAlarm(SnmpAlarmData data, String workId, int expectedId) {
        try {
            AlarmDelegate.delegateAlarmData(data);
        } catch (FmException e) {
            LOG.error("Failed to delegate alarm: workId={}, alarmId={}",
                    workId, data.getAlarmId(), e);
        }
    }

    private void processNotification(SnmpAlarmData data) {
        try {
            AlarmDelegate.delegateAlarmData(data);
        } catch (FmException e) {
            LOG.error("Failed to process notification alarm: {}", data.getAlarmId(), e);
        }
    }

    private void processRegularAlarm(SnmpAlarmData data) {
        try {
            AlarmDelegate.delegateAlarmData(data);
        } catch (FmException e) {
            LOG.error("Failed to process regular alarm: {}", data.getAlarmId(), e);
        }
    }
}
