package com.zte.ums.em.fm.adapter.trap.entity;

import com.zte.ums.em.fm.adapter.alarm.entity.SnmpAlarmData;

import java.util.concurrent.Delayed;
import java.util.concurrent.TimeUnit;

/**
 * DelayClearAlarm - Represents a CLEAR alarm held in delay queue.
 * When a CLEAR alarm arrives before its corresponding RAISE alarm
 * (out-of-order), it is held in this delayed wrapper to wait for
 * the RAISE to arrive first.
 *
 * After CLEAR_DELAY_MS (30s), the clear alarm is processed regardless
 * of whether the raise arrived.
 */
public class DelayClearAlarm implements Delayed {

    private final SnmpAlarmData alarmData;
    private final String workId;
    private final int originalExpectedId;
    private final long expireTimeMs;

    public DelayClearAlarm(SnmpAlarmData alarmData, String workId,
                           int originalExpectedId, long expireTimeMs) {
        this.alarmData = alarmData;
        this.workId = workId;
        this.originalExpectedId = originalExpectedId;
        this.expireTimeMs = expireTimeMs;
    }

    public SnmpAlarmData getAlarmData() { return alarmData; }
    public String getWorkId() { return workId; }
    public int getOriginalExpectedId() { return originalExpectedId; }

    @Override
    public long getDelay(TimeUnit unit) {
        return unit.convert(expireTimeMs - System.currentTimeMillis(), TimeUnit.MILLISECONDS);
    }

    @Override
    public int compareTo(Delayed other) {
        long diff = this.expireTimeMs - ((DelayClearAlarm) other).expireTimeMs;
        return Long.compare(diff, 0);
    }
}
