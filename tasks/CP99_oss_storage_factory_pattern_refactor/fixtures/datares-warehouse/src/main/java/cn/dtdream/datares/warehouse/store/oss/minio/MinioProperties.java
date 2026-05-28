package cn.dtdream.datares.warehouse.store.oss.minio;

import cn.dtdream.datares.common.constans.ConfigConstants;
import cn.dtdream.datares.common.constans.SignConstants;
import cn.dtdream.datares.warehouse.constants.WarehouseConstants;
import org.springframework.boot.context.properties.ConfigurationProperties;
import org.springframework.boot.context.properties.bind.DefaultValue;

/**
 * Minio configuration information
 */
@ConfigurationProperties(prefix = ConfigConstants.FunctionModuleConstants.WAREHOUSE
    + SignConstants.DOT
    + WarehouseConstants.OSS
    + SignConstants.DOT
    + WarehouseConstants.OssName.MINIO)
public record MinioProperties(@DefaultValue("false") boolean enabled,
                              @DefaultValue("http://127.0.0.1:9000") String endpoint,
                              @DefaultValue("minioadmin") String accessKey,
                              @DefaultValue("minioadmin") String secretKey,
                              @DefaultValue("default") String bucketName) {
}
