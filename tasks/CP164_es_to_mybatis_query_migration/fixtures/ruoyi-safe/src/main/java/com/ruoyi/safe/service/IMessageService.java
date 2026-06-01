package com.ruoyi.safe.service;

import com.baomidou.mybatisplus.core.metadata.IPage;
import com.baomidou.mybatisplus.extension.service.IService;
import com.ruoyi.safe.domain.Message;
import com.ruoyi.safe.domain.form.MessageQryForm;
import com.ruoyi.safe.domain.vo.MessageVO;

public interface IMessageService extends IService<Message> {

    IPage<MessageVO> queryPage(MessageQryForm form, int pageNum, int pageSize);

    MessageVO getDetailById(Long id);
}
