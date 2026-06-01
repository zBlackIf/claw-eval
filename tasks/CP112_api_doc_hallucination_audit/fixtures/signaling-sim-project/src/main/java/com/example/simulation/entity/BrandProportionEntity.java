package com.example.simulation.entity;

import lombok.Data;

@Data
public class BrandProportionEntity {
    private Long id;
    private String nfSubServiceType;
    private String brand;
    private Double proportion;
    private String province;
    private String updateTime;
}
