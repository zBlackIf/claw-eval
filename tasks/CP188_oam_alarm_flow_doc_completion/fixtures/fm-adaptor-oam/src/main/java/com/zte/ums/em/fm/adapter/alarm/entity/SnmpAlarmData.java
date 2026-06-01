package com.zte.ums.em.fm.adapter.alarm.entity;

/**
 * SnmpAlarmData - Alarm data carrier from SNMP trap parsing.
 * Created by receiveTrap() after OID mapping, passed through the entire pipeline.
 */
public class SnmpAlarmData {

    /** Alarm type: alarmRaised, alarmCleared, alarmChanged */
    private String type;

    /** Unique alarm identifier */
    private String alarmId;

    /** Network Element name */
    private String neName;

    /** NE type identifier (e.g., "OAM-PTN", "OAM-SDH") */
    private String neType;

    /** Alarm severity: critical, major, minor, warning, info */
    private String alarmPerceivedSeverity;

    /** SNMP trap notification ID for OAM ordering */
    private String sendNotificationId;

    /** Managed Element ID for Kafka topic routing */
    private String meId;

    /** Whether this is a notification-type alarm (vs event-type) */
    private boolean notification;

    /** Physical location: rack number */
    private String rackNo;

    /** Physical location: slot number */
    private String slotNo;

    /** Physical location: port number */
    private String portNo;

    /** Alarm probable cause description */
    private String probableCause;

    /** Additional text / alarm detail */
    private String additionalText;

    /** Timestamp from the NE */
    private long neTimestamp;

    // Getters and setters
    public String getType() { return type; }
    public void setType(String type) { this.type = type; }
    public String getAlarmId() { return alarmId; }
    public void setAlarmId(String alarmId) { this.alarmId = alarmId; }
    public String getNeName() { return neName; }
    public void setNeName(String neName) { this.neName = neName; }
    public String getNeType() { return neType; }
    public void setNeType(String neType) { this.neType = neType; }
    public String getAlarmPerceivedSeverity() { return alarmPerceivedSeverity; }
    public void setAlarmPerceivedSeverity(String severity) { this.alarmPerceivedSeverity = severity; }
    public String getSendNotificationId() { return sendNotificationId; }
    public void setSendNotificationId(String id) { this.sendNotificationId = id; }
    public String getMeId() { return meId; }
    public void setMeId(String meId) { this.meId = meId; }
    public boolean isNotification() { return notification; }
    public void setNotification(boolean notification) { this.notification = notification; }
    public String getRackNo() { return rackNo; }
    public void setRackNo(String rackNo) { this.rackNo = rackNo; }
    public String getSlotNo() { return slotNo; }
    public void setSlotNo(String slotNo) { this.slotNo = slotNo; }
    public String getPortNo() { return portNo; }
    public void setPortNo(String portNo) { this.portNo = portNo; }
    public String getProbableCause() { return probableCause; }
    public void setProbableCause(String probableCause) { this.probableCause = probableCause; }
    public String getAdditionalText() { return additionalText; }
    public void setAdditionalText(String additionalText) { this.additionalText = additionalText; }
    public long getNeTimestamp() { return neTimestamp; }
    public void setNeTimestamp(long neTimestamp) { this.neTimestamp = neTimestamp; }
}
