/**
* Generate time : 2026-05-15 10:39:10
* Version : 6.0.731.201709180824
*/
package com.baosight.egdw.jh.sm.domain;
import com.baosight.iplat4j.core.util.NumberUtils;
import java.math.BigDecimal;
import com.baosight.iplat4j.core.ei.EiColumn;
import com.baosight.iplat4j.core.data.DaoEPBase;
import java.util.HashMap;
import java.util.Map;
import com.baosight.iplat4j.core.util.StringUtils;

/**
* JHSM3110
* table comment : 主原料明细成本标准（可手工）用于全流程
*/
public class JHSM3110 extends DaoEPBase {

                private String recId = " ";		/* 记录ID*/
                private String account = "";		/* 帐套*/
                private String year = " ";		/* YEAR*/
                private String edition = " ";		/* EDITION*/
                private String costCenter = " ";		/* COST_CENTER - DB column is VARCHAR(4) */
                private String productCode4 = " ";		/* PRODUCT_CODE_4 - VARCHAR(100) composite */
                private String wce = " ";		/* WCE - DB column is VARCHAR(5) */
                private BigDecimal plungeWeight1 = new BigDecimal("0");
                private BigDecimal plungeWeight2 = new BigDecimal("0");
                private BigDecimal lastYearPlunge = new BigDecimal("0");
                private BigDecimal stdPlunge = new BigDecimal("0");
                private String plungePrdtCode = " ";
                private String modifyName = " ";
                private String modifyDate = " ";
                private String key = " ";

                private String productCode;
                private String stNo;       /* derived from PRODUCT_CODE_4 substr(6,8) */
                private String thickChr;
                private String widthChr;
                private String coatingType;
                private String ctrlRollCode;
                private String heatProcLog;
                private String sgSign;
                private String yEdition;
                private String inProductCode;

    /**
     * initialize the metadata
     */
    public void initMetaData() {
        EiColumn eiColumn;

        eiColumn = new EiColumn("recId");
        eiColumn.setFieldLength(32);
        eiColumn.setDescName("记录ID");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("account");
        eiColumn.setFieldLength(4);
        eiColumn.setDescName("帐套");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("year");
        eiColumn.setFieldLength(4);
        eiColumn.setDescName("YEAR");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("edition");
        eiColumn.setFieldLength(2);
        eiColumn.setDescName("EDITION");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("costCenter");
        eiColumn.setFieldLength(4);
        eiColumn.setDescName("COST_CENTER");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("productCode4");
        eiColumn.setFieldLength(100);
        eiColumn.setDescName("PRODUCT_CODE_4");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("wce");
        eiColumn.setFieldLength(5);
        eiColumn.setDescName("WCE");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("plungeWeight1");
        eiColumn.setType("N");
        eiColumn.setScaleLength(8);
        eiColumn.setFieldLength(30);
        eiColumn.setDescName("PLUNGE_WEIGHT_1");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("plungeWeight2");
        eiColumn.setType("N");
        eiColumn.setScaleLength(8);
        eiColumn.setFieldLength(30);
        eiColumn.setDescName("PLUNGE_WEIGHT_2");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("lastYearPlunge");
        eiColumn.setType("N");
        eiColumn.setScaleLength(8);
        eiColumn.setFieldLength(30);
        eiColumn.setDescName("LAST_YEAR_PLUNGE");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("stdPlunge");
        eiColumn.setType("N");
        eiColumn.setScaleLength(8);
        eiColumn.setFieldLength(30);
        eiColumn.setDescName("STD_PLUNGE");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("plungePrdtCode");
        eiColumn.setFieldLength(20);
        eiColumn.setDescName("PLUNGE_PRDT_CODE");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("modifyName");
        eiColumn.setFieldLength(30);
        eiColumn.setDescName("MODIFY_NAME");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("modifyDate");
        eiColumn.setFieldLength(10);
        eiColumn.setDescName("MODIFY_DATE");
        eiMetadata.addMeta(eiColumn);

        eiColumn = new EiColumn("key");
        eiColumn.setFieldLength(50);
        eiColumn.setDescName("KEY");
        eiMetadata.addMeta(eiColumn);
    }

    public String getRecId() { return recId; }
    public void setRecId(String recId) { this.recId = recId; }
    public String getAccount() { return account; }
    public void setAccount(String account) { this.account = account; }
    public String getYear() { return year; }
    public void setYear(String year) { this.year = year; }
    public String getEdition() { return edition; }
    public void setEdition(String edition) { this.edition = edition; }
    public String getCostCenter() { return costCenter; }
    public void setCostCenter(String costCenter) { this.costCenter = costCenter; }
    public String getProductCode4() { return productCode4; }
    public void setProductCode4(String productCode4) { this.productCode4 = productCode4; }
    public String getWce() { return wce; }
    public void setWce(String wce) { this.wce = wce; }
    public BigDecimal getPlungeWeight1() { return plungeWeight1; }
    public void setPlungeWeight1(BigDecimal plungeWeight1) { this.plungeWeight1 = plungeWeight1; }
    public BigDecimal getPlungeWeight2() { return plungeWeight2; }
    public void setPlungeWeight2(BigDecimal plungeWeight2) { this.plungeWeight2 = plungeWeight2; }
    public BigDecimal getLastYearPlunge() { return lastYearPlunge; }
    public void setLastYearPlunge(BigDecimal lastYearPlunge) { this.lastYearPlunge = lastYearPlunge; }
    public BigDecimal getStdPlunge() { return stdPlunge; }
    public void setStdPlunge(BigDecimal stdPlunge) { this.stdPlunge = stdPlunge; }
    public String getPlungePrdtCode() { return plungePrdtCode; }
    public void setPlungePrdtCode(String plungePrdtCode) { this.plungePrdtCode = plungePrdtCode; }
    public String getModifyName() { return modifyName; }
    public void setModifyName(String modifyName) { this.modifyName = modifyName; }
    public String getModifyDate() { return modifyDate; }
    public void setModifyDate(String modifyDate) { this.modifyDate = modifyDate; }
    public String getKey() { return key; }
    public void setKey(String key) { this.key = key; }
    public String getProductCode() { return productCode; }
    public void setProductCode(String productCode) { this.productCode = productCode; }
    public String getStNo() { return stNo; }
    public void setStNo(String stNo) { this.stNo = stNo; }
    public String getThickChr() { return thickChr; }
    public void setThickChr(String thickChr) { this.thickChr = thickChr; }
    public String getWidthChr() { return widthChr; }
    public void setWidthChr(String widthChr) { this.widthChr = widthChr; }
    public String getCoatingType() { return coatingType; }
    public void setCoatingType(String coatingType) { this.coatingType = coatingType; }
    public String getCtrlRollCode() { return ctrlRollCode; }
    public void setCtrlRollCode(String ctrlRollCode) { this.ctrlRollCode = ctrlRollCode; }
    public String getHeatProcLog() { return heatProcLog; }
    public void setHeatProcLog(String heatProcLog) { this.heatProcLog = heatProcLog; }
    public String getSgSign() { return sgSign; }
    public void setSgSign(String sgSign) { this.sgSign = sgSign; }
    public String getYEdition() { return yEdition; }
    public void setYEdition(String yEdition) { this.yEdition = yEdition; }
    public String getInProductCode() { return inProductCode; }
    public void setInProductCode(String inProductCode) { this.inProductCode = inProductCode; }
}
