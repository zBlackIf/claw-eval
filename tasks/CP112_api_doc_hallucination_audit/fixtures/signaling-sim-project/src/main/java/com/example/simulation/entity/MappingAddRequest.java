package com.example.simulation.entity;

import lombok.Data;

@Data
public class MappingAddRequest {
    private Long screenId;
    private Long simulationId;
    private String descriptionZh;
    private String descriptionEn;
    private Integer sortOrder;
    private Boolean enabled;
}
