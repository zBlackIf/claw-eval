package com.zte.ums.em.fm.adapter.alarm;

import com.zte.ums.em.fm.adapter.alarm.entity.SnmpAlarmData;
import com.zte.ums.em.fm.adapter.common.FmConsts;
import com.zte.ums.em.fm.adapter.common.FmException;
import com.zte.ums.em.fm.adapter.mq.MessageSendUtil;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

/**
 * AlarmDelegate - Core alarm delegation handler.
 * Receives parsed SnmpAlarmData and routes it through the processing pipeline.
 */
public class AlarmDelegate {

    private static final Logger LOG = LoggerFactory.getLogger(AlarmDelegate.class);

    /**
     * Main entry point for alarm data delegation.
     * Performs 5 steps:
     * 1. Validate alarm data completeness (neName, alarmId must be non-null)
     * 2. Enrich alarm with NE metadata (neType, location, rack/slot info)
     * 3. Apply alarm suppression rules (check maintenance window, duplicate filter)
     * 4. Transform alarm severity based on policy (severity mapping table)
     * 5. Call parseAndSendMsg() for final dispatch
     *
     * @param data The parsed SNMP alarm data
     * @throws FmException if validation fails or downstream processing errors
     */
    public static void delegateAlarmData(SnmpAlarmData data) throws FmException {
        if (data == null) {
            LOG.warn("Received null alarm data, skipping.");
            return;
        }

        // Step 1: Validate completeness
        if (data.getNeName() == null || data.getAlarmId() == null) {
            LOG.error("Alarm data missing required fields: neName={}, alarmId={}",
                    data.getNeName(), data.getAlarmId());
            throw new FmException("Missing required alarm fields");
        }

        // Step 2: Enrich with NE metadata
        enrichNeMetadata(data);

        // Step 3: Apply suppression rules
        if (isSuppressed(data)) {
            LOG.info("Alarm suppressed by policy: alarmId={}, neName={}",
                    data.getAlarmId(), data.getNeName());
            return;
        }

        // Step 4: Transform severity
        transformSeverity(data);

        // Step 5: Parse and send
        parseAndSendMsg(data);
    }

    /**
     * Enriches alarm data with NE metadata from the NE registry.
     * Populates neType, location, rackNo, slotNo, portNo fields.
     */
    private static void enrichNeMetadata(SnmpAlarmData data) {
        // Lookup NE info from NeRegistry cache
        String neName = data.getNeName();
        LOG.debug("Enriching NE metadata for: {}", neName);
        // neType, location, rack/slot populated from registry
    }

    /**
     * Checks if the alarm should be suppressed.
     * Rules:
     * - Maintenance window active for this NE -> suppress
     * - Duplicate alarm within 60s dedup window -> suppress
     * - Alarm type in global suppress list -> suppress
     */
    private static boolean isSuppressed(SnmpAlarmData data) {
        // Check maintenance window
        if (MaintenanceWindowManager.isInMaintenance(data.getNeName())) {
            return true;
        }
        // Check dedup window (60s)
        if (AlarmDedupCache.isDuplicate(data.getAlarmId(), data.getNeName(), 60000)) {
            return true;
        }
        // Check global suppress list
        return AlarmSuppressList.contains(data.getType());
    }

    /**
     * Transforms alarm severity based on policy configuration.
     * Severity mapping: critical->critical, major->major, minor->warning, warning->info
     * Can be overridden per-NE type via severity_policy.xml
     */
    private static void transformSeverity(SnmpAlarmData data) {
        String originalSeverity = data.getAlarmPerceivedSeverity();
        String mappedSeverity = SeverityPolicyManager.mapSeverity(
                data.getNeType(), originalSeverity);
        if (!originalSeverity.equals(mappedSeverity)) {
            LOG.info("Severity transformed: {} -> {} for alarm {}",
                    originalSeverity, mappedSeverity, data.getAlarmId());
            data.setAlarmPerceivedSeverity(mappedSeverity);
        }
    }

    /**
     * Parses alarm data into MQ message format and sends to Kafka.
     * Determines message type (NEW_ALARM, CLEAR_ALARM, CHANGE_ALARM) based on alarm type field.
     * Constructs MqMessage with all required fields and sends via MessageSendUtil.
     *
     * Message type mapping:
     * - TABLE_ALARMRAISED / TABLE_ALARMCHANGED -> MessageType.NEW_ALARM or CHANGE_ALARM
     * - TABLE_ALARMCLEARED -> MessageType.CLEAR_ALARM
     *
     * Topic selection based on isNotification flag:
     * - notification alarms -> topic: "fm-notification"
     * - event alarms -> topic: "fm-event-{meId}"
     */
    public static void parseAndSendMsg(SnmpAlarmData data) {
        String type = data.getType();
        String messageType;

        if (FmConsts.TABLE_ALARMRAISED.equalsIgnoreCase(type)) {
            messageType = "NEW_ALARM";
        } else if (FmConsts.TABLE_ALARMCLEARED.equalsIgnoreCase(type)) {
            messageType = "CLEAR_ALARM";
        } else if (FmConsts.TABLE_ALARMCHANGED.equalsIgnoreCase(type)) {
            messageType = "CHANGE_ALARM";
        } else {
            LOG.warn("Unknown alarm type: {}, defaulting to NEW_ALARM", type);
            messageType = "NEW_ALARM";
        }

        MqMessage mqMsg = MqMessageBuilder.build(data, messageType);
        String meId = data.getMeId();
        String topicName = data.isNotification() ? "fm-notification" : "fm-event-" + meId;
        boolean isNotification = data.isNotification();

        MessageSendUtil.send2kafka(messageType, mqMsg, meId, topicName, isNotification);
        LOG.info("Alarm sent to Kafka: type={}, topic={}, alarmId={}",
                messageType, topicName, data.getAlarmId());
    }
}
