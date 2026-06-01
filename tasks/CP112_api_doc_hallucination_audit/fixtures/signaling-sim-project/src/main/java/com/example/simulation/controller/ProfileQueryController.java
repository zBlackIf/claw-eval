package com.example.simulation.controller;

import com.example.simulation.entity.BrandProportionEntity;
import com.example.simulation.entity.MappingAddRequest;
import com.example.simulation.entity.MappingDeleteRequest;
import com.example.simulation.entity.TerminalProfileEntity;
import com.example.simulation.entity.TerminalBrandEntity;
import com.example.simulation.entity.ResultModel;

import javax.ws.rs.*;
import javax.ws.rs.core.MediaType;
import java.util.List;

@Path("/api/simulation-service/v1/config")
public class ProfileQueryController {

    /**
     * Get list of provinces.
     */
    @GET
    @Path("/province")
    @Produces(MediaType.APPLICATION_JSON)
    public ResultModel listProvince() {
        return new ResultModel();
    }

    /**
     * Get terminal brand behavior list.
     */
    @GET
    @Path("/terminal-action")
    @Produces(MediaType.APPLICATION_JSON)
    public ResultModel listBrandBehavior() {
        return new ResultModel();
    }

    /**
     * Update terminal brand behavior.
     */
    @POST
    @Path("/terminal-action")
    @Consumes(MediaType.APPLICATION_JSON)
    public ResultModel updateBrandBehavior(@Body TerminalProfileEntity entity) {
        return new ResultModel();
    }

    /**
     * Reset terminal action to default.
     */
    @PUT
    @Path("/terminal-action")
    public ResultModel resetActionToDefault() {
        return new ResultModel();
    }

    /**
     * Delete terminal brand behavior by brand and behavior_id.
     */
    @DELETE
    @Path("/terminal-action")
    public ResultModel deleteBehaviorBrand(
            @QueryParam("brand") String brand,
            @QueryParam("behavior_id") String behaviorId) {
        return new ResultModel();
    }

    /**
     * Add new terminal brands (batch).
     */
    @POST
    @Path("/terminal-brand")
    @Consumes(MediaType.APPLICATION_JSON)
    public ResultModel addBrand(@Body List<TerminalBrandEntity> brands) {
        return new ResultModel();
    }

    /**
     * Update brand proportion configuration.
     */
    @POST
    @Path("/brand-proportion")
    @Consumes(MediaType.APPLICATION_JSON)
    public ResultModel updateBrandProportion(@Body List<BrandProportionEntity> proportions) {
        return new ResultModel();
    }

    /**
     * Get brand proportion by nfSubServiceType.
     */
    @GET
    @Path("/brand-proportion")
    @Produces(MediaType.APPLICATION_JSON)
    public ResultModel getBrandProportion(
            @QueryParam("nf_sub_service_type") String nfSubServiceType,
            @QueryParam("brand") String brand) {
        return new ResultModel();
    }

    /**
     * Restore base station default values.
     */
    @PUT
    @Path("/base-station/default")
    public ResultModel restoreBaseStationDefault(
            @QueryParam("brand") String brand) {
        return new ResultModel();
    }
}
