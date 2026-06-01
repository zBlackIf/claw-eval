package cn.iocoder.yudao.module.external.enums;

/**
 * 打印模式枚举
 */
public enum PrintModeEnum {

    NEW_PRINT(0, "新码打印"),
    REPRINT(1, "重打"),
    SUPPLEMENT(2, "补打");

    private final Integer code;
    private final String desc;

    PrintModeEnum(Integer code, String desc) {
        this.code = code;
        this.desc = desc;
    }

    public Integer getCode() {
        return code;
    }

    public String getDesc() {
        return desc;
    }
}
