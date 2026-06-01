package com.ruoyi.safe.service.impl;

import cn.hutool.core.util.StrUtil;
import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.plugins.pagination.Page;
import com.ruoyi.common.core.service.BaseServiceImpl;
import com.ruoyi.safe.domain.Message;
import com.ruoyi.safe.domain.form.MessageQryForm;
import com.ruoyi.safe.domain.vo.MessageVO;
import com.ruoyi.safe.mapper.MessageMapper;
import com.ruoyi.safe.service.IMessageService;
import com.ruoyi.safe.service.search.UniversalSearchService;
import com.ruoyi.safe.service.search.UniversalSearchAuthFilter;
import org.springframework.beans.BeanUtils;
import org.springframework.beans.factory.annotation.Autowired;
import org.springframework.stereotype.Service;

import java.util.HashMap;
import java.util.Map;

@Service
public class MessageServiceImpl extends BaseServiceImpl<MessageMapper, Message> implements IMessageService {

    @Autowired
    private UniversalSearchService universalSearchService;

    @Override
    public IPage<MessageVO> queryPage(MessageQryForm form, int pageNum, int pageSize) {
        Map<String, Object> filter = buildBaseWrapper(form);
        UniversalSearchAuthFilter authFilter = new UniversalSearchAuthFilter();
        authFilter.setIndex("sh_message");
        authFilter.setFilter(filter);
        return universalSearchService.searchPage(new Page<>(pageNum, pageSize), authFilter, Message.class)
                .convert(this::toDetailVO);
    }

    @Override
    public MessageVO getDetailById(Long id) {
        Message po = getById(id);
        if (po == null) {
            return null;
        }
        return toDetailVO(po);
    }

    private Map<String, Object> buildBaseWrapper(MessageQryForm form) {
        Map<String, Object> filter = new HashMap<>();
        if (form.getMsgType() != null) {
            filter.put("msgType", form.getMsgType());
        }
        if (StrUtil.isNotBlank(form.getKeyword())) {
            filter.put("keyword", form.getKeyword());
            filter.put("keyword_fields", "title,content");
        }
        filter.put("delFlag", 0);
        return filter;
    }

    private MessageVO toDetailVO(Message po) {
        MessageVO vo = new MessageVO();
        BeanUtils.copyProperties(po, vo);
        return vo;
    }
}
