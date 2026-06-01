package com.demo.entity;

/**
 * 用户实体
 */
public class UserEntity {

    private Long id;

    /** 用户名 */
    private String username;

    /** 状态：0=禁用, 1=启用 */
    private Integer status;

    /** 性别：0=未知, 1=男, 2=女 */
    private Integer gender;

    /** 部门ID（外键） */
    private Long departmentId;

    public UserEntity() {}

    public UserEntity(Long id, String username, Integer status, Integer gender, Long departmentId) {
        this.id = id;
        this.username = username;
        this.status = status;
        this.gender = gender;
        this.departmentId = departmentId;
    }

    public Long getId() { return id; }
    public void setId(Long id) { this.id = id; }
    public String getUsername() { return username; }
    public void setUsername(String username) { this.username = username; }
    public Integer getStatus() { return status; }
    public void setStatus(Integer status) { this.status = status; }
    public Integer getGender() { return gender; }
    public void setGender(Integer gender) { this.gender = gender; }
    public Long getDepartmentId() { return departmentId; }
    public void setDepartmentId(Long departmentId) { this.departmentId = departmentId; }
}
