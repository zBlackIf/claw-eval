package com.example.simulation.entity;

import lombok.Data;

import java.util.List;

@Data
public class MappingDeleteRequest {
    private Long screenId;
    private List<Long> mappingIds;
}
