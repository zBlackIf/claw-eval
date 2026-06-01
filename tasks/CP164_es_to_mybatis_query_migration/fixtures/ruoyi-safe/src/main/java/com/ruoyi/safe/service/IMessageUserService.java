package com.ruoyi.safe.service;

import com.baomidou.mybatisplus.extension.service.IService;
import com.ruoyi.safe.domain.MessageUser;

public interface IMessageUserService extends IService<MessageUser> {

    Long countUnreadByUserId(Long userId);

    void markAsRead(Long messageId, Long userId);
}
