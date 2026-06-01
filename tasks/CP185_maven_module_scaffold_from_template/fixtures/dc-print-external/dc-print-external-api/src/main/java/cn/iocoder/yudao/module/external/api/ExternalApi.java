package cn.iocoder.yudao.module.external.api;

/**
 * 外接系统 API 接口
 * 供其他模块依赖调用
 */
public interface ExternalApi {

    /**
     * 查询作业状态
     */
    Integer getJobStatus(String jobCode);

    /**
     * 提交作业
     */
    String submitJob(String productCode, String batchNo, Integer printMode);
}
