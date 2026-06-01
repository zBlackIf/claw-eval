package com.example.simulation.entity;

import lombok.Data;

@Data
public class TerminalBrandEntity {
    private Long id;
    private String brand;
    private String model;
    private String networkCapability;
    private Boolean enabled;
}
