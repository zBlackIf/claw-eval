package com.example.simulation.controller;

import com.example.simulation.entity.MappingAddRequest;
import com.example.simulation.entity.MappingDeleteRequest;
import com.example.simulation.entity.ResultModel;

import javax.ws.rs.*;
import javax.ws.rs.core.MediaType;
import java.util.List;

@Path("/api/simulation-service/v1/mapping")
public class MappingController {

    /**
     * Add a new simulation screen mapping.
     */
    @POST
    @Path("/screen")
    @Consumes(MediaType.APPLICATION_JSON)
    public ResultModel addMapping(@Body MappingAddRequest request) {
        return new ResultModel();
    }

    /**
     * Delete simulation screen mappings.
     * NOTE: Uses POST method (not DELETE) with MappingDeleteRequest body.
     */
    @POST
    @Path("/screen/delete")
    @Consumes(MediaType.APPLICATION_JSON)
    public ResultModel deleteMapping(@Body MappingDeleteRequest request) {
        return new ResultModel();
    }
}
