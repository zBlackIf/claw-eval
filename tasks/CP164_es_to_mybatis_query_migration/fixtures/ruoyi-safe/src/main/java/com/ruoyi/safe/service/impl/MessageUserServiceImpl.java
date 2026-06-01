package com.ruoyi.safe.service.impl;

import com.baomidou.mybatisplus.core.conditions.query.LambdaQueryWrapper;
import com.baomidou.mybatisplus.core.conditions.update.LambdaUpdateWrapper;
import com.ruoyi.common.core.service.BaseServiceImpl;
import com.ruoyi.safe.domain.MessageUser;
import com.ruoyi.safe.mapper.MessageUserMapper;
import com.ruoyi.safe.service.IMessageUserService;
import com.ruoyi.safe.service.search.UniversalSearchService;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class MessageUserServiceImpl extends BaseServiceImpl<MessageUserMapper, MessageUser> implements IMessageUserService {

    @Autowired
    private UniversalSearchService universalSearchService;

    @Override
    public Long countUnreadByUserId(Long userId) {
        Map<String, Object> filter = new HashMap<>();
        filter.put("userId", userId);
        filter.put("readFlag", MessageUser.READ_FLAG_UN_READ);
        return universalSearchService.count("sh_message_user", filter);
    }

    @Override
    public void markAsRead(Long messageId, Long userId) {
        update(new LambdaUpdateWrapper<MessageUser>()
                .eq(MessageUser::getMessageId, messageId)
                .eq(MessageUser::getUserId, userId)
                .set(MessageUser::getReadFlag, MessageUser.READ_FLAG_READ));
    }
}
