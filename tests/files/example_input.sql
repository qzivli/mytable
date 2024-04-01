CREATE TABLE `AllocationInput`
(
    `id`                        int AUTO_INCREMENT NOT NULL COMMENT '主键',
    `code`                      varchar(100) NOT NULL COMMENT '唯一编码',
    `allocatedAmount`           AmountInput  NOT NULL COMMENT '分摊金额',
    -- 使用decimal类型，保证一个费用的所有分摊的比例加起来刚好是100%
    `allocatedRatio`            decimal(20,2)      NOT NULL COMMENT '分摊比例',  -- type: BigDecimal
    `coverDepartmentBizCode`    varchar(100) NULL COMMENT '分摊部门业务编码',
    `coverDepartmentDingtalkId` varchar(300) NULL COMMENT '分摊部门钉钉ID',
    `coverDepartmentName`       varchar(100) NULL COMMENT '分摊部门名称',
    `coverDepartmentFullname`   varchar(1000) NULL COMMENT '分摊部门名称全称（由程序添加）',
    `coverUserName`             varchar(100) NULL COMMENT '分摊人员名称',
    -- NOTE: 每刻一开始出现typo，后来的文档中改正了typo，但数据中还是coverEmpoyeeNo
    `coverEmpoyeeNo`            varchar(100) NULL COMMENT '分摊人员工号',
    `approvedBaseAmount`        AmountInput  NOT NULL COMMENT '审批通过的本币金额',
    `coverDimensionExt`         List<String> NULL COMMENT '根据选项组分摊的选项组code',
    -- 官方文档里 customObject 不可为空值，但实际数据中可能为空
    `customObject`              Map<String,Object> NULL COMMENT '自定义字段的信息',
    `accrualReconcile`          AccrualReconcileInput NULL COMMENT '预提核销',

    -- 以下字段为程序添加
    `cover_jfxm_code` varchar(100) null __lift comment '分摊交付项目编码',
    `cover_jfxm_text` varchar(1000) null __lift comment '分摊交付项目名称',

    `cover_yfxm_code` varchar(100) null __lift comment '分摊研发项目编码',
    `cover_yfxm_text` varchar(1000) null __lift comment '分摊研发项目名称',

    `cover_zxxm_code` varchar(100) null __lift comment '分摊咨询项目编码',
    `cover_zxxm_text` varchar(1000) null __lift comment '分摊咨询项目名称',

    PRIMARY KEY (`id`),
    CONSTRAINT __unique_code UNIQUE KEY (`code`)
) ENGINE = InnoDB
  CHARSET = utf8mb4
  COMMENT = '分摊信息';

CREATE TABLE `AmountInput`
(
    id        int AUTO_INCREMENT NOT NULL COMMENT '主键',
    currency  varchar(10) NOT NULL COMMENT '货币',
    amount    decimal(20, 2)     NOT NULL COMMENT '金额',
    amountStr varchar(100) NULL COMMENT '金额（组合字符串）',
    primary key (`id`)
) ENGINE = InnoDB
  CHARSET = utf8mb4
  COMMENT = '金额';

CREATE TABLE `DateTimeInput`
(
    `id`        int AUTO_INCREMENT NOT NULL COMMENT '主键',
    `startTime` timestamp          NULL comment '开始时间时间戳',
    `endTime`   timestamp          NULL comment '结束时间时间戳',
    PRIMARY KEY (`id`)
) ENGINE = InnoDB
  CHARSET = utf8mb4
  COMMENT = '时间';

CREATE TABLE `ExpenseInput`
(
    `id`                          int AUTO_INCREMENT NOT NULL COMMENT '主键',
    `code`                        varchar(100)       NOT NULL UNIQUE comment '费用code，唯一标识',
    `expenseTypeBizCode`          varchar(100)       NOT NULL comment '费用类型编码',
    `expenseTypeName`             varchar(100)       NOT NULL comment '费用类型名称',
    `viceExpenseTypeBizCode`      varchar(100)       NULL comment '辅助费用类型编码',
    `viceExpenseTypeName`         varchar(100)       NULL comment '辅助费用类型名称',
    `consumeAmount`               AmountInput        NOT NULL comment '消费金额',
--     `consumeBaseAmount`           AmountInput        NULL comment '消费本币金额',
    `approvedAmount`              AmountInput        NOT NULL comment '审批通过金额',
--     `approvedBaseAmount`          AmountInput        NOT NULL comment '审批通过本币金额',
    `comments`                    varchar(1000)      NULL comment '备注',
    `airClass`                    varchar(100)       NULL comment '舱位(只有飞机标准关联了该费用类型才会有该字段)',
    `trainSeat`                   varchar(100)       NULL comment '座位(只有火车标准关联了该费用类型才会有该字段)',
    `consumeTime`                 DateTimeInput      NOT NULL comment '消费时间(字段类型具体看表单配置)',
    `consumeLocation`             CityInput          NULL comment '消费城市(字段类型具体看表单配置)',
    `invoiceList`                 List<InvoiceInput> NULL comment '发票(可能为多张)',
    `attachments`                 List<AttachInput>  NULL comment '附件(可能为多个)',
    `allocationList`              List<AllocationInput> NOT NULL comment '分摊信息，每个费用至少有一条分摊',
    `customObject`                Map<String, Object>               NULL comment '非系统级字段的一个Map集合',
    `invoiceStatus`               int                NULL comment '发票状态',
    `invoiceSubmitTime`           long               NULL comment '发票到票时间',
    `invoiceExpectSubmitTime`     long               NULL comment '发票预计到票时间',
    `status`                      varchar(32)        NULL comment '费用状态',
    `corpExpense`                 boolean            NOT NULL comment '是否为对公费用',
    -- enums: 业务类型 ALL_RECEIPTS-全部到票，SOME_RECEIPTS-部分到票，NO_RECEIPT-未到票， RECEIPT_DEDUCTION-到票核销
    `corpType`                    varchar(100)       NULL comment '业务类型',
    `receiptAmount`               AmountInput        NULL comment '到票金额',
    `nonReceiptAmount`            AmountInput        NULL comment '未到票金额',
    `forecastReceiptDate`         DateTimeInput      NULL comment '预计到票日期',
    `tradingPartnerBizCode`       varchar(100)       NULL comment '往来单位业务编码',
    `tradingPartnerParentBizCode` varchar(100)       NULL comment '当前往来单位的上一级分类的编码',
    `tradingPartnerName`          varchar(150)       NULL comment '往来单位名称',
    `recordDeductionAmount`       AmountInput        NULL comment '核销未到票记录金额',
    -- enums:
    `splitTag`                    varchar(100)       NOT NULL comment '费用拆分状态，NOT_SPLIT-未被拆分，SPLIT_SOURCE-拆分来源，SPLIT_TARGET-拆分后费用',
    `splitSourceCode`             varchar(150)       NULL comment '拆分来源的费用Code',
    `deductionList`               List<ExpenseDeductionInput> NULL comment '对公费用核销的数据',
    `sourceId`                    varchar(150)       NULL comment '第三方流水Id',
    `sourceType`                  varchar(100)       NULL comment '第三方类型',
    `consumeToAcceptExchangeRate` decimal(20, 2)            NOT NULL comment '消费币种到收款币种汇率',
    `acceptToBaseExchangeRate`    decimal(20, 2)            NOT NULL comment '收款币种到本币汇率',

    -- enums:
    -- `settleType` varchar(100) NULL comment '',

    PRIMARY KEY (`id`),
    CONSTRAINT __unique_code UNIQUE KEY (`code`)
) ENGINE = InnoDB
  CHARSET = utf8mb4
  COMMENT = '费用';


CREATE TABLE `Reimburse` (
    `id` int AUTO_INCREMENT NOT NULL COMMENT '主键',
    `formCode` varchar(100) NOT NULL UNIQUE COMMENT '单据号',
    `formSubTypeBizCode` varchar(100) NOT NULL COMMENT '单据小类编码',
    `formSubTypeName` varchar(150) NOT NULL COMMENT '单据小类名称',
    `formStatus` varchar(100) NOT NULL comment '单据状态',
    `reimburseName` varchar(600) NOT NULL COMMENT '单据名称（事由）',
    `payeeAccount` AccountInput NULL COMMENT '收款账户',
    -- Java generic syntax
    `payerAccounts` List<PayInfoInput> NULL COMMENT '支付信息',
    `consumeApplicationCodes` List<String> __assoc Preconsume.formCode NULL COMMENT '关联申请单的codes',
    `contractNumbers` List<String> __assoc Contract.formCode NULL COMMENT '关联合同编号列表',
    `amount` AmountInput NOT NULL COMMENT '报销金额',
    `customObject` Map<String, Object> NULL COMMENT '自定义数据',
    `travelRouteList` List<TravelRoute> NULL COMMENT '行程列表',
    `expenseList` List<ExpenseInput> NULL comment '费用列表',

    -- will extract from customObject
    `project_code` varchar(255) NULL __lift COMMENT '项目编号',
    `project_text` varchar(255) NULL __lift COMMENT '项目名称',

    PRIMARY KEY (`id`),
    CONSTRAINT __unique_code UNIQUE KEY (`formCode`),
    INDEX (`formStatus`),
    INDEX (`project_code`),
    INDEX (`project_text`),
    __common_code (`formCode`) -- 子表和子表的字表都添加该字段
) ENGINE = InnoDB
  CHARSET = utf8mb4
  COMMENT = '报销单';


CREATE TABLE `Preconsume` (
    `id` int AUTO_INCREMENT NOT NULL COMMENT '主键',
    `formDataCode` varchar(100) NOT NULL comment '单据号（单据内码）',
    `formCode` varchar(100) NOT NULL UNIQUE comment '单据号',
    `formSubTypeBizCode` varchar(100) NOT NULL comment '单据小类编码',
    `formSubTypeName` varchar(150) NOT NULL comment '单据小类名称',
    `formStatus` varchar(100) NOT NULL comment '单据状态',
    `preConsumeName` varchar(300) NOT NULL comment '申请单名称（事由）',

    `customObject` Map<String, Object> NULL COMMENT '自定义数据',
    `travelRouteList` List<TravelRoute> NULL COMMENT '行程列表',

    `correlatedReimburseCodes` List<String> __assoc Reimburse.formCode NULL comment '关联的报销单单号',

    -- will extract from customObject
    `project_code` varchar(255) NULL __lift COMMENT '项目编号',
    `project_text` varchar(255) NULL __lift COMMENT '项目名称',

    PRIMARY KEY (`id`),
    CONSTRAINT __unique_code UNIQUE KEY (`formCode`),
    INDEX (`formStatus`),
    INDEX (`project_code`),
    INDEX (`project_text`),
    __common_code (`formCode`) -- 子表和子表的字表都添加该字段
)
    ENGINE=InnoDB, CHARSET=utf8mb4, COMMENT = '申请单';

