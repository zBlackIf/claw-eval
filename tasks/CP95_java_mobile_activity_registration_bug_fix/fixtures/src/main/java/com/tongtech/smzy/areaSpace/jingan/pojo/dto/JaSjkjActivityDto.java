package com.tongtech.smzy.areaSpace.jingan.pojo.dto;

import java.util.Date;

public class JaSjkjActivityDto {
    private Long id;
    private String activityName;
    private String activityDesc;
    private Date startTime;
    private Date endTime;
    private Integer maxParticipants;
    private Integer currentParticipants;
    private String contactPhone;
    private String contactName;
    private Integer status; // 0: draft, 1: active, 2: expired

    // getters and setters
    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getActivityName() { return activityName; }
    public void setActivityName(String activityName) { this.activityName = activityName; }
    public String getActivityDesc() { return activityDesc; }
    public void setActivityDesc(String activityDesc) { this.activityDesc = activityDesc; }
    public Date getStartTime() { return startTime; }
    public void setStartTime(Date startTime) { this.startTime = startTime; }
    public Date getEndTime() { return endTime; }
    public void setEndTime(Date endTime) { this.endTime = endTime; }
    public Integer getMaxParticipants() { return maxParticipants; }
    public void setMaxParticipants(Integer maxParticipants) { this.maxParticipants = maxParticipants; }
    public Integer getCurrentParticipants() { return currentParticipants; }
    public void setCurrentParticipants(Integer currentParticipants) { this.currentParticipants = currentParticipants; }
    public String getContactPhone() { return contactPhone; }
    public void setContactPhone(String contactPhone) { this.contactPhone = contactPhone; }
    public String getContactName() { return contactName; }
    public void setContactName(String contactName) { this.contactName = contactName; }
    public Integer getStatus() { return status; }
    public void setStatus(Integer status) { this.status = status; }
}
