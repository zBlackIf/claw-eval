package com.example.simulation.entity;

import lombok.Data;

@Data
public class TerminalProfileEntity {
    private Long id;
    private String brand;
    private String behaviorId;
    private String behaviorName;
    private Double callRatio;
    private Double dataRatio;
    private Double smsRatio;
    private Double voLteRatio;
    private Double vonrRatio;
    private String networkType;
    private String province;
    private String nfSubServiceType;
    private String updateTime;
}
