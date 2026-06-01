package com.example.simulation.controller;

import com.example.simulation.entity.BrandProportionEntity;
import com.example.simulation.entity.ResultModel;

import javax.ws.rs.*;
import javax.ws.rs.core.Context;
import javax.ws.rs.core.MediaType;
import javax.servlet.http.HttpServletRequest;
import javax.servlet.http.HttpServletResponse;
import java.io.InputStream;
import java.util.List;

import org.glassfish.jersey.media.multipart.FormDataContentDisposition;
import org.glassfish.jersey.media.multipart.FormDataParam;

@Path("/api/simulation-service/v1/profile")
public class ProfileModelController {

    /**
     * Upload terminal behavior data file.
     * Only accepts multipart file upload, no additional parameters.
     */
    @POST
    @Path("/behavior")
    @Consumes(MediaType.MULTIPART_FORM_DATA)
    public ResultModel uploadTerminalData(
            @FormDataParam("file") InputStream fileInputStream,
            @FormDataParam("file") FormDataContentDisposition fileDetail) {
        // implementation
        return new ResultModel();
    }

    /**
     * Download terminal behavior data.
     * No query parameters required.
     */
    @GET
    @Path("/behavior")
    public void downloadTerminalData(
            @Context HttpServletRequest request,
            @Context HttpServletResponse response) {
        // implementation
    }

    /**
     * Upload base station data file.
     * Only accepts multipart file upload, no additional parameters.
     */
    @POST
    @Path("/base-station")
    @Consumes(MediaType.MULTIPART_FORM_DATA)
    public ResultModel uploadStationData(
            @FormDataParam("file") InputStream fileInputStream,
            @FormDataParam("file") FormDataContentDisposition fileDetail) {
        // implementation
        return new ResultModel();
    }

    /**
     * Download base station data.
     * Requires province query parameter.
     */
    @GET
    @Path("/base-station")
    public void downloadStationData(
            @Context HttpServletRequest request,
            @Context HttpServletResponse response,
            @QueryParam("province") String province) {
        // implementation
    }

    /**
     * Upload access rate data file.
     * Accepts multipart file upload with province as FormDataParam.
     */
    @POST
    @Path("/access-rate")
    @Consumes(MediaType.MULTIPART_FORM_DATA)
    public ResultModel uploadAccessRateData(
            @FormDataParam("file") InputStream fileInputStream,
            @FormDataParam("file") FormDataContentDisposition fileDetail,
            @FormDataParam("province") String province) {
        // implementation
        return new ResultModel();
    }

    /**
     * Download access rate data.
     * Requires province query parameter.
     */
    @GET
    @Path("/access-rate")
    public void downloadAccessRateData(
            @Context HttpServletRequest request,
            @Context HttpServletResponse response,
            @QueryParam("province") String province) {
        // implementation
    }
}
