package cn.iocoder.yudao.module.external.controller.admin;

import cn.iocoder.yudao.framework.common.pojo.CommonResult;
import cn.iocoder.yudao.framework.common.pojo.PageResult;
import cn.iocoder.yudao.module.external.domain.MesJobRecord;
import cn.iocoder.yudao.module.external.pojo.dto.MesJobRecordSearchDTO;
import cn.iocoder.yudao.module.external.pojo.vo.MesJobRecordVO;
import cn.iocoder.yudao.module.external.service.MesJobRecordService;
import io.swagger.v3.oas.annotations.Operation;
import io.swagger.v3.oas.annotations.tags.Tag;
import lombok.RequiredArgsConstructor;
import org.springframework.web.bind.annotation.*;

import static cn.iocoder.yudao.framework.common.pojo.CommonResult.success;

@Tag(name = "MES 作业记录")
@RestController
@RequestMapping("/external/mes-job-record")
@RequiredArgsConstructor
public class MesJobRecordController {

    private final MesJobRecordService mesJobRecordService;

    @GetMapping("/page")
    @Operation(summary = "分页查询作业记录")
    public CommonResult<PageResult<MesJobRecord>> getPage(MesJobRecordSearchDTO searchDTO) {
        return success(mesJobRecordService.getPage(searchDTO));
    }

    @GetMapping("/{id}")
    @Operation(summary = "获取作业记录详情")
    public CommonResult<MesJobRecord> getDetail(@PathVariable Long id) {
        return success(mesJobRecordService.getById(id));
    }

    @PostMapping("/create")
    @Operation(summary = "创建作业记录")
    public CommonResult<Boolean> create(@RequestBody MesJobRecord record) {
        mesJobRecordService.create(record);
        return success(true);
    }
}
