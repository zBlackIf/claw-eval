package cn.iocoder.yudao.module.external.service;

/**
 * 设备 API 服务接口
 */
public interface DeviceApiService {

    /**
     * 获取设备状态
     */
    String getDeviceStatus(String deviceCode);

    /**
     * 发送打印指令
     */
    boolean sendPrintCommand(String deviceCode, String jobCode);
}
