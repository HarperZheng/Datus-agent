
# 1 概述
## 1.1 报表分类
财政非税收入管理系统中的报表从业务使用用户的角度来看，分成两类：
| 序号 | 报表类型 | 说明 |
|:----|:---:|:---:|
| 1 | 财政端报表 | 用于财政用户进行查询本级财政所属单位的非税收入数据情况 |
| 2 | 单位端报表 | 用于单位用户查询本单位的相关数据 |

从数据在系统存储位置来看，分成两类：
| 序号 | 报表类型 | 说明 |
|:----|:---:|:---:|
| 1 | 查询库 | 通过ETL方式将数据抽取转换到宽表方式存储在OLAP类型数据库中，目前省份系统大多数使用Clickhouse |
| 2 | 实时生产库 | 用于保存非税收入系统实时产生的数据，目前大多数采用Oracle数据库，信创改造后大多数是达梦数据库 |

从报表数据生成角度来看，分成两类：
| 序号 | 报表类型 | 说明 |
|:----|:---:|:---:|
| 1 | 内置报表 | 通过代码计算来生成报表 |
| 2 | 自定义报表 | 通过自定义报表工具编写SQL语句和查询条件来生成报表 |

本文档下面部分描述的报表仅包含自定义报表部分。

## 1.2 查询条件与SQL参数说明
- 在自定义报表中，查询条件在用户提交查询按钮的时候会先根据定义转换成相应的参数值，然后对自定义报表中的SQL语句进行替换，最后才将转换后的SQL提交数据库执行。
- SQL语句中的参数以${参数名}方式表示，如${fbankcode}。

# 2 查询库报表
该部分报表数据来源于查询库数据（**Clickhouse**）

## 2.1 罚缴分离统计表-财政端

### 报表样式
![](report_images/image2.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:---|:---:|:---:| :---: | :---: | :---: |
| 1 | 区划 | 否 | | ${frgncode} | fne_paybook_full_high.fchgrgncode |
| 2 | 到账银行 | 否 | | ${fbankcode} | fne_paybook_full_high.ftransrecbankcode|
| 3 | 到账日期 | 是 | 包含起始日期和结束日期，默认为本月 | \${enterdate_bgn}，${enterdate_end} | fne_paybook_full_high.fenterdate |

### 报表语句
``` SQL
---- 按开票点统计
select
fp.fchgrgncode  as FBELONGRGNCODE,  --区划编码
fp.fchgrgnname  as FBELONGRGNNAME, --区划名称
fp.ftransrecbankcode as FRECBANKCODE,
fp.ftransrecbankname as FRECBANKNAME, --收款银行名称
count(distinct fp.fpaycode) as FPAYBOOKNUM, --收款笔数
count(distinct fp.fpaycode) * 1.5 as FPROCEDURESAMT, -- 手续费
sum(case when fp.fitemname in ('公安罚没','道路交通违法罚款') then fp.fimamt else 0 end) as FPENALTYAMT,  --罚款
sum(case when fp.fitemname in ('罚没滞纳金','滞纳金') then fp.fimamt else 0 end) as FLATEPAYAMT,          --滞纳金
sum(case when fp.fitemname in ('公安罚没','道路交通违法罚款','罚没滞纳金','滞纳金') then fp.fimamt else 0 end) as FTOTALAMT --合计
from fne_paybook_full_high fp
where fp.fchgrgncode = '${frgncode}'
and fp.fchgagenidcode='0f9df0a7e04b4c7586a6343a7eca924c'
and fp.fitemidcode in ('640020001059','640020001097','640020000446','640020000445')
and fp.ftransrecaccttype = '1'
and fp.ftransrecbankcode = '${fbankcode}'
and fp.fenterdate >= '${enterdate_bgn}'
and fp.fenterdate <= '${enterdate_end}'
group by fp.fchgrgncode,fp.fchgrgnname,fp.ftransrecbankcode, fp.ftransrecbankname
order by fp.fchgrgncode,fp.ftransrecbankcode

```

## 2.2 非税收入电子票据汇总记账凭证（查询库）-财政端

### 报表样式

![](report_images/image4.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: | :---:| :---: |
| 1 | 记账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${pay_bgndate}，${pay_enddate} | fne_paybook_full_high.fdate |
| 2 | 区划 | 否 | | ${frgncode} | fne_paybook_full_high.fchgrgncode |
| 3 | 单位 | 否 | | ${fagenidcode} | fne_paybook_full_high.fchgagenidcode |
| 4 | 到账银行 | 否 | | ${fbankcode} | fne_paybook_full_high.recbankcode |
| 5 | 收费项目 | 否 | | ${fitemidcode} | fne_paybook_full_high.fitemidcode |
| 6 | 资金性质 | 否 | | ${ftype} | fne_paybook_full_high.ffundsnaturecode |

### 报表语句
``` SQL
select
'#{pay_bgndate}' as pay_bgndate,
'#{pay_enddate}' as pay_enddate,
'#{bgndate}' as hz_bgndate,
'#{enddate}' as hz_enddate,
'#{fre_bgndate}' as fre_bgndate,
'#{fre_enddate}' as fre_enddate,
total.fchgagenidcode,
total.fchgagencode as FAGENCODE,
total.fchgagenname as FAGENNAME,

total.fitemidcode,
total.fitemname as FITEMNAME,
total.fitemcode as FITEMCODE,
total.fsubname as FSUBNAME,
total.fsubcode as FSUBCODE,
count(*) as FCONFIRMNUM,
sum(total.famt) as FCONFIRMAMT,
sum(case when total.enterdate='' then null else 1 end) as FRECEIVENUM,
sum(case when total.enterdate='' then null else total.famt end) as FRECEIVEAMT
from (select
'1' as ftype,
fpaycode,
fchgagenidcode,
fdate,
ftransdate,
fenterdate, --划转到账时间
fchgagencode,
fchgagenname,
fitemidcode,
fitemname,
fitemcode,
fsubname,
fsubcode,
ifnull(fimamt,famt) as famt,
if('#{frecacct}'<>'' and '#{frecacct}'=ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', ftransrecbankcode, ftransrecbankcode_last) as recbankcode,
if(sfechz='0', fstats, fstats_last) as stats,
if(sfechz='0', fistransfer, fistransfer_last) as istransfer,
if(sfechz='0', fisenter, fisenter_last) as isenter,
if(sfechz='0', ftransno, ftransno_last) as transno,
if(sfechz='0', ftransrecacct, ftransrecacct_last) as transrecacct,
if(sfechz='0', ftransdate, ftransdate_last) as transdate,
if(sfechz='0', fenterdate, fenterdate_last) as enterdate,
fsortno
from fne_paybook_full_high
where  fpaycode not in (select fpaycode from une_paybook_paycode)
and fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and transdate >= '${bgndate}'
and transdate <= '${enddate}'
and enterdate >= '${fre_bgndate}'
and enterdate <= '${fre_enddate}'
and fitemidcode = '${fitemidcode}'
and recbankcode = '${fbankcode}'
and transrecacct = '${frecacct}'
and ffundsnaturecode = '${ftype}'
and fpaycode not in (select fpaycode from fne_unknown_capital_balance)
union all
select
'2' as ftype,
fpaycode,
fchgagenidcode,
fdate,
ftransdate,
freceiveddate, --划转到账时间
fchgagencode,
fchgagenname,
fitemidcode,
fitemname,
fitemcode,
fsubname,
fsubcode,
ifnull(fimamt,famt) as famt,
'' as sfechz,
'' as frecbankcode,
fstats,
fistransfer,
fisenter,
ftransno,
ftransrecacct,
ftransdate,
freceiveddate as enterdate,
fsortno
from fne_paybook_full_high
where fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and ftransdate >= '${bgndate}'
and ftransdate <= '${enddate}'
and fitemidcode = '${fitemidcode}'
and freceiveddate>= '${fre_bgndate}'
and freceiveddate<= '${fre_enddate}'
and ffundsnaturecode = '${ftype}'
and fpaycode in (select fpaycode from fne_unknown_capital_balance ucb left join fne_unknown_capital uc on uc.fid = ucb.funknownfundsid   where ucb.fagenidcode in '${fagenidcode}' and ucb.fbankcode='${fbankcode}' and uc.frecacct='${frecacct}' )
) total

where 1=1

group by total.fchgagenidcode,
total.fchgagencode,
total.fchgagenname,
total.fitemidcode,
total.fitemname,
total.fitemcode,
total.fsubcode,
total.fsubname
order by FAGENCODE,FITEMCODE

```

## 2.3 非税收入缴库汇总表（查询库）-财政经常用-财政端

### 报表样式
![](report_images/image6.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 区划 | 否 | 默认为空，表示本级财政 | ${frgncode} | fne_paybook_full_high.fchgrgncode |
| 2 | 执收单位 | 否 | | ${fagenidcode} | fne_paybook_full_high.fchgagenidcode |
| 3 | 专户到账日期 | 否 | 包含起始日期和结束日期，默认为空 | **${ftransdate_bgn},${ftransdate_end}** | fne_treasury_transfer_main.fdate,fne_paybook_full_high fpfh.freceiveddate,fne_paybook_full_high.fenterdate |
| 4 | 缴库生单日期 | 是 | 包含起始日期和结束日期，默认为本月,**一个字段多个表使用** | ${fsenddate_bgn},${fsenddate_end} | fne_treasury_transfer_main.fdate |
| 5 | 缴库日期 | 否 | 包含起始日期和结束日期，默认为空 | ${fenterdate_bgn},${fenterdate_end} | fne_treasury_transfer_main.ftransdate |
| 6 | 专户帐号 | 否 | 默认为空 | ${frecacct} | fne_paybook_full_high.frecacct |
| 7 | 缴库单号 | 否 | 默认为空 | ${ftransno} | fne_treasury_transfer_main.ftransno |
| 8 | 缴库状态 | 否 | 默认为空,case | ${fisjk} | fne_paybook_full_high.ftransdate,fne_paybook_full_high.ftransno |
| 9 | 代理银行 | 否 | 默认为空 | ${fbankcode} | fne_treasury_transfer_main.fbankcode |
| 10 | 缴库类型 | 否 | 默认为空 | ${ftreatype} | fne_treasury_transfer_main.ftreatype |
| 11 | 预算科目 | 否 | 默认为空 | ${fsubcode} | fne_paybook_full_high.frecsubcode,fne_paybook_full_high.fsubcode |

### 报表语句
``` sql
-- 2025-04-27 新增clickhouse 非税收入缴库汇总表 gzj
select ffn.fchgrgncode as fchgrgncode,
ffn.fchgrgnname as fchgrgnname,
ffn.fchgagenidcode as fchgagenidcode,
ffn.fchgagencode as fchgagencode,
ffn.fchgagenname as fchgagenname,
fttn.fdate as fpaydate, --缴库生单日期
fttn.fsenddate as fsenddate, --缴库发送日期
fttn.ftransdate as ftransdate, --国库扣款日期
fttn.fenterdate as fenterdate, --入库日期
fttn.fenterstatus as fenterstatus,
fttn.fbankcode as fbankcode, --付款银行
fttn.fbankname as fbankname, --付款银行
fttn.frecacct as frecacct,  --收款国库账号
fttn.ftransno as ftransno,
ffn.frecsubcode as fsubcode,
ffn.frecsubname as fsubname,
sum(ffn.fimamt) as fimamt,
case when fttn.ftransdate != '' then '缴库到账' when fttn.ftransno != '' then '缴库在途' else '未缴库' end as showstatus,
case when fttn.ftreatype = '2' then '人工缴库'  when  fttn.ftreatype in ('0','1') then 'tips缴库' else '' end as treatype

from  (
select fchgrgncode,
fchgrgnname,
fchgagenidcode,
fchgagencode,
fchgagenname,
fpaycode,
frecsubcode,
frecsubname,
fitemcode,
fitemname,
fimamt,
frecfundsnaturecode, --资金性质代码
fcollectid,
ftreasuryno,
fid,
if('#{frecacct}'<>'' and '#{frecacct}'=ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', ftransrecacct, ftransrecacct_last) as recacct,
if(sfechz='0', fenterdate , fenterdate_last) as enterdate
from fne_paybook_full_high fpfh
where  substr(ffundsnaturecode,1,1) = '1'
and fpaycode not in (select fpaycode from une_paybook_paycode)
and fpaycode not in (select fpaycode from fne_unknown_capital_balance where fagenidcode in '${fagenidcode}'
and fagenidcode in (select fagenidcode from fab_agen where frgncode='${frgncode}' and fisfinal='1') )
and fbgtstyle = '1'
and fdatatag < '3'
and fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and frecsubcode = '${fsubcode}'
and fitemcode = '${fitemcode}'
and recacct = '${frecacct}'
and enterdate >= '${ftransdate_bgn}'
and enterdate <= '${ftransdate_end}'
union all
select fchgrgncode,
fchgrgnname,
fchgagenidcode,
fchgagencode,
fchgagenname,
fpaycode,
fsubcode,
fsubname,
fitemcode,
fitemname,
fimamt,
ffundsnaturecode, --资金性质代码
fcollectid,
ftreasuryno,
fid,
'' as sfechz,  --是否二次划转
frecacct,
freceiveddate
from fne_paybook_full_high fpfh
where  substr(ffundsnaturecode,1,1) = '1'
and fpaycode not in (select fpaycode from une_paybook_paycode)
and fpaycode in (select fpaycode from fne_unknown_capital_balance where fagenidcode in '${fagenidcode}'
and fagenidcode in (select fagenidcode from fab_agen where frgncode='${frgncode}' and fisfinal='1') )
and fbgtstyle = '1'
and fdatatag < '3'
and fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and fsubcode = '${fsubcode}'
and fitemcode = '${fitemcode}'
and frecacct = '${frecacct}'
and freceiveddate >= '${ftransdate_bgn}'
and freceiveddate <= '${ftransdate_end}'
) ffn

left join
(select fchgrgncode,
fpayacct, --付款账户
fpaybankopenname, --付款开户行名称
fpayacctname, --付款账户名称
frecorgcode, --收款国库代码
frecacctname, --收款账户名称
frecacct, --收款账号
fdate, --缴库生单日期
fsenddate, --缴库发送日期
ftransdate, --国库扣款日期
fenterdate, --入库日期
fenterstatus,
fbankcode,
fbankname, --付款银行
ftransno,
ftranscollectid ,--关联条件
ftreatype  --缴库方式
from fne_treasury_transfer_main
where fchgrgncode = '${frgncode}'
and fdate >= '${ftransdate_bgn}'
and fdate >= '${fsenddate_bgn}'
and fdate <= '${fsenddate_end}'
and ftransdate >= '${fenterdate_bgn}'
and ftransdate <= '${fenterdate_end}'
and ftransno = '${ftransno}'
and fbankcode = '${fbankcode}'

) fttn
on fttn.ftransno = ffn.ftreasuryno

left join afa_res_dictitem ard
on ffn.frecfundsnaturecode = ard.fcode
and ard.fdictcode='120'
where showstatus = '${fisjk}'
and treatype = '${ftreatype}'
and fttn.fdate >= '${fsenddate_bgn}'
and fttn.fdate <= '${fsenddate_end}'
and fttn.ftransdate >= '${fenterdate_bgn}'
and fttn.ftransdate <= '${fenterdate_end}'
and fttn.ftransno = '${ftransno}'
and fttn.fbankcode = '${fbankcode}'
group by
ffn.fchgrgncode,
ffn.fchgrgnname,
ffn.fchgagenidcode,
ffn.fchgagencode,
ffn.fchgagenname,
fttn.fdate,
fttn.fsenddate,
fttn.ftransdate,
fttn.fenterdate,
fttn.fenterstatus,
fttn.fbankcode,
fttn.fbankname,
fttn.frecacct,
fttn.ftransno,
ffn.frecsubcode,
ffn.frecsubname,
showstatus,
treatype
order by fttn.fdate,
ffn.fchgrgncode,
ffn.fchgagencode,
fttn.ftransno
```

## 2.4 非税收入缴库明细表（查询库）-财政经常用-财政端

### 报表样式

![](report_images/image8.png)

### 报表查询条件
| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 区划 | 否 | 默认为空，表示本级财政 | ${frgncode} | fne_paybook_full_high.fchgrgncode |
| 2 | 执收单位 | 否 | 一个字段多个表使用 | ${fagenidcode} | fne_paybook_full_high.fchgagenidcode,fne_unknown_capital_balance.fagenidcode |
| 3 | 专户到账日期 | 否 | 包含起始日期和结束日期，默认为空,**一个字段多个表使用** | \${ftransdate_bgn},${ftransdate_end} | fne_treasury_transfer_main.fdate,fne_paybook_full_high.freceiveddate |
| 4 | 缴库生单日期 | 是 | 包含起始日期和结束日期，默认为本月 | \${fsenddate_bgn},${fsenddate_end} | fne_treasury_transfer_main.fdate |
| 5 | 缴库日期 | 否 | 包含起始日期和结束日期，默认为空 | \${fenterdate_bgn},${fenterdate_end} | fne_treasury_transfer_main.ftransdate |
| 6 | 专户帐号 | 否 | 默认为空 | ${frecacct} | fne_paybook_full_high.frecacct |
| 7 | 缴库单号 | 否 | 默认为空 | ${ftransno} | fne_treasury_transfer_main.ftransno |
| 8 | 缴库状态 | 否 | 默认为空 | ${fisjk} | fne_paybook_full_high.ftransdate,fne_paybook_full_high.ftransno |
| 9 | 代理银行 | 否 | 默认为空 | ${fbankcode} | fne_treasury_transfer_main.fbankcode |
| 10 | 缴库类型 | 否 | 默认为空 | ${ftreatype} | fne_treasury_transfer_main.ftreatype |
| 11 | 预算科目 | 否 | 默认为空 | ${fsubcode} | fne_paybook_full_high.fsubcode |
| 12 | 收费项目 | 否 | 默认为空 | ${fitemcode} | fne_paybook_full_high.fitemcode |

### 报表语句
``` sql
-- 2025-03-24 新增clickhouse 非税收入缴库明细表 gzj
select ffn.fchgrgncode as fchgrgncode,
ffn.fchgrgnname as fchgrgnname,
ffn.fchgagencode as fchgagencode,
ffn.fchgagenname as fchgagenname,
ffn.fpaycode as fpaycode,
fttn.fpayacct as fpayacct, --付款账户
fttn.fpaybankopenname as fpaybankopenname, --付款开户行名称
fttn.fpayacctname as fpayacctname, --付款账户名称
fttn.frecorgcode as frecorgcode, --收款国库代码
fttn.frecacctname as frecacctname, --收款账户名称
fttn.frecacct as frecacct, --收款账号
fttn.fdate as fpaydate, --缴库生单日期
fttn.fsenddate as fsenddate, --缴库发送日期
fttn.ftransdate as ftransdate, --国库扣款日期
fttn.fenterdate as fenterdate, --入库日期
fttn.fenterstatus as fenterstatus,
fttn.fbankname as fbankname, --付款银行
fttn.ftransno as ftransno,
ffn.frecsubcode as frecsubcode,
ffn.frecsubname as frecsubname,
ffn.fitemcode as fitemcode,
ffn.fitemname as fitemname,
ffn.fimamt as fimamt,
ard.fname as ffundsortname,
case when fttn.ftransdate != '' then '缴库到账' when fttn.ftransno != '' then '缴库在途' else '未缴库' end as showstatus,
case when fttn.ftreatype = '2' then '人工缴库'  when fttn.ftreatype in ('0','1') then 'tips缴库' else '' end as treatype
from  (
select fchgrgncode,
fchgrgnname,
fchgagencode,
fchgagenname,
fpaycode,
frecsubcode,
frecsubname,
fitemcode,
fitemname,
fimamt,
frecfundsnaturecode, --资金性质代码
fcollectid,
ftreasuryno,
fid,
if('#{frecacct}'<>'' and '#{frecacct}'=ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', ftransrecacct, ftransrecacct_last) as recacct,
if(sfechz='0', fenterdate , fenterdate_last) as enterdate
from fne_paybook_full_high fpfh
where  substr(ffundsnaturecode,1,1) = '1'
and fpaycode not in (select fpaycode from une_paybook_paycode)
and fpaycode not in (select fpaycode from fne_unknown_capital_balance where fagenidcode in '${fagenidcode}'
and fagenidcode in (select fagenidcode from fab_agen where frgncode='${frgncode}' and fisfinal='1') )
and fbgtstyle = '1'
and fdatatag < '3'
and fchgrgncode = '${frgncode}'
and fchgagenidcode = '${fagenidcode}'
and frecsubcode = '${fsubcode}'
and fitemcode = '${fitemcode}'
and recacct = '${frecacct}'
and enterdate >= '${ftransdate_bgn}'
and enterdate <= '${ftransdate_end}'
union all
select fchgrgncode,
fchgrgnname,
fchgagencode,
fchgagenname,
fpaycode,
fsubcode,
fsubname,
fitemcode,
fitemname,
fimamt,
ffundsnaturecode, --资金性质代码
fcollectid,
ftreasuryno,
fid,
'' as sfechz,  --是否二次划转
frecacct,
freceiveddate
from fne_paybook_full_high fpfh
where  substr(ffundsnaturecode,1,1) = '1'
and fpaycode not in (select fpaycode from une_paybook_paycode)
and fpaycode in (select fpaycode from fne_unknown_capital_balance where fagenidcode in '${fagenidcode}'
and fagenidcode in (select fagenidcode from fab_agen where frgncode='${frgncode}' and fisfinal='1') )
and fbgtstyle = '1'
and fdatatag < '3'
and fchgrgncode = '${frgncode}'
and fchgagenidcode = '${fagenidcode}'
and fsubcode = '${fsubcode}'
and fitemcode = '${fitemcode}'
and frecacct= '${frecacct}'
and freceiveddate >= '${ftransdate_bgn}'
and freceiveddate <= '${ftransdate_end}'
) ffn

left join
(select fchgrgncode,
fpayacct, --付款账户
fpaybankopenname, --付款开户行名称
fpayacctname, --付款账户名称
frecorgcode, --收款国库代码
frecacctname, --收款账户名称
frecacct, --收款账号
fdate, --缴库生单日期
fsenddate, --缴库发送日期
ftransdate, --国库扣款日期
fenterdate, --入库日期
fenterstatus,
fbankcode,
fbankname, --付款银行
ftransno,
ftranscollectid, --关联条件
ftreatype --缴库方式
from fne_treasury_transfer_main
where fchgrgncode = '${frgncode}'
and fdate >= '${ftransdate_bgn}'
and fdate >= '${fsenddate_bgn}'
and fdate <= '${fsenddate_end}'
and ftransdate >= '${fenterdate_bgn}'
and ftransdate <= '${fenterdate_end}'
and ftransno = '${ftransno}'
and fbankcode = '${fbankcode}'

) fttn
on fttn.ftransno = ffn.ftreasuryno

left join afa_res_dictitem ard
on ffn.frecfundsnaturecode = ard.fcode
and ard.fdictcode='120'
where showstatus = '${fisjk}'
and treatype = '${ftreatype}'
and fttn.fdate >= '${fsenddate_bgn}'
and fttn.fdate <= '${fsenddate_end}'
and fttn.ftransdate >= '${fenterdate_bgn}'
and fttn.ftransdate <= '${fenterdate_end}'
and fttn.ftransno = '${ftransno}'
and fttn.fbankcode = '${fbankcode}'

order by fttn.fdate,
fttn.fchgrgncode,
ffn.fchgagencode,
fttn.ftransno,
ffn.fpaycode,
ffn.fitemcode,
ffn.fid

```

## 2.5 非税收入会计记账汇总表（查询库）-财政端

### 报表样式

![](report_images/image10.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 区划 | 否 | 默认为空，表示本级财政 | ${frgncode} | fne_paybook_full_high.fchgrgncode |
| 2 | 执收单位 | 否 | | ${fagenidcode} | fne_paybook_full_high.fchgagenidcode |
| 3 | 到账日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${date_bgn},${date_end} | fne_paybook_full_high.enterdate |
| 4 | 缴库日期 | 否 | 包含起始日期和结束日期，默认为空 | ${jkdate_bgn},${jkdate_end} | fne_treasury_transfer_new.fdate |
| 5 | 专户帐号 | 否 | 默认为空 | ${facct} | fne_unknown_capital.frecacct |
| 6 | 到账银行 | 否 | 默认为空 | ${fbankcode} | fne_paybook_full_high.recbankcode |

### 报表语句
``` sql
select fp.enterdate as freceiveddate,
fp.fitemcode as fitemcode,
fp.fitemname as fitemname,
if(fp.recbankcode='', ub.fbankcode, fp.recbankcode) as frecbankcode,
if(fp.recbankcode='', '('||ub.fbankcode||')'||fb.fname, '('||fp.recbankcode||')'||fp.recbankname) as frecbankname,
sum(fp.fimamt) as fimamt,
replaceAll(replaceAll(replaceAll(toString(arrayDistinct(groupArray(case when ft.fdate='' then null else ft.fdate end))), '[', ''), ']', ''), '''', '')  as jk_date,
sum(if(ft.fdate<>'', fp.fimamt, null)) as jk_amt,
replaceAll(replaceAll(replaceAll(toString(arrayDistinct(groupArray(if(fp.fbgtstyle<>'1', fp.transdate, null)))), '[', ''), ']', ''), '''', '') as zh_date,
sum(if(fp.transdate<>'' and fp.fbgtstyle<>'1', fp.fimamt, null)) as zh_amt,
ifnull(fimamt,toDecimal64(0,6)) - ifnull(jk_amt,toDecimal64(0,6)) - ifnull(zh_amt,toDecimal64(0,6)) as ye
from (select
if('#{facct}'<>'' and '#{facct}'=ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', ftransrecbankcode, ftransrecbankcode_last) as recbankcode,
if(sfechz='0', ftransrecbankname, ftransrecbankname_last) as recbankname,
if(sfechz='0', fstats, fstats_last) as stats,
if(sfechz='0', fistransfer, fistransfer_last) as istransfer,
if(sfechz='0', fisenter, fisenter_last) as isenter,
if(sfechz='0', ftransno, ftransno_last) as transno,
if(sfechz='0', ftransrecacct, ftransrecacct_last) as transrecacct,
if(sfechz='0', ftransdate, ftransdate_last) as transdate,
if(sfechz='0', fenterdate, fenterdate_last) as enterdate,
fitemcode,
fitemname,
ifnull(fimamt,famt) as fimamt,
ftreasuryno ,
fbgtstyle, fpaycode
from fne_paybook_full_high
where fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and enterdate >= '${date_bgn}'
and enterdate <= '${date_end}'
and fitemidcode = '${fitemidcode}'
and recbankcode = '${fbankcode}'
and fpaycode not in (select fpaycode from fne_unknown_capital_balance)
union all
select
'' as sfechz,  --是否二次划转
'' as recbankcode,
'' as recbankname,
fstats as stats,
fistransfer as istransfer,
fisenter as isenter,
ftransno as transno,
ftransrecacct as transrecacct,
ftransdate as transdate,
freceiveddate as enterdate,
fitemcode,
fitemname,
ifnull(fimamt,famt) as fimamt,
ftreasuryno ,
fbgtstyle, fpaycode
from fne_paybook_full_high
where fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and freceiveddate >= '${date_bgn}'
and freceiveddate <= '${date_end}'
and fitemidcode = '${fitemidcode}'
and fpaycode in (
select fpaycode
from fne_unknown_capital_balance ucb
left join fne_unknown_capital uc on uc.fid = ucb.funknownfundsid
where ucb.fagenidcode in '${fagenidcode}' and ucb.fbankcode='${fbankcode}'
and uc.frecacct='${facct}'  )
) fp
left join (
select ftransno,max(t.fdate) as fdate
from fne_treasury_transfer_new  t
where t.fdate >= '${date_bgn}'
and t.fdate >= '${jkdate_bgn}'
and t.fdate <= '${jkdate_end}'
and fchgrgncode = '${frgncode}'
and '#{facct}' = ''
group by ftransno
) ft
on fp.ftreasuryno = ft.ftransno
left join fne_unknown_capital_balance ub on ub.fpaycode = fp.fpaycode
left join afa_res_dictitem fb on ub.fbankcode = fb.fcode and fb.fdictcode = '152'
where  ft.fdate >= '${jkdate_bgn}'
and  ft.fdate <= '${jkdate_end}'
group by fp.enterdate,
fp.fitemcode,
fp.fitemname,
frecbankcode,
frecbankname
order by freceiveddate,fitemcode,frecbankcode

```

## 2.6 单位缴款统计汇总表（查询库）-财政经常用-财政端

### 报表样式
![](report_images/image12.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收区划 | 否 | 默认为空，表示本级财政 | ${frgncode} | fne_paybook_full_high.fchgrgncode |
| 2 | 执收单位 | 否 | | ${fagenidcode} | fne_paybook_full_high.fchgagenidcode |
| 3 | 缴款日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${pay_bgndate},${pay_enddate} | fne_paybook_full_high.fdate |
| 4 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${fre_bgndate},${fre_enddate} | fne_paybook_full_high.enterdate |
| 5 | 收费项目 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_full_high.fitemidcode |
| 6 | 到账银行 | 否 | 默认为空 | ${fbankcode} | fne_paybook_full_high.recbankcode |
| 7 | 资金性质 | 否 | 默认为空 | ${ftype} | fne_paybook_full_high.ffundsnaturecode |
| 8 | 收款人帐号 | 否 | 默认为空 | ${frecacct} | fne_paybook_full_high.transrecacct |
| 9 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${bgndate},${enddate} | fne_paybook_full_high.transdate |

### 报表语句
``` SQL
/*une_paybook_paycode线下退付*/
select * from
(select
'#{pay_bgndate}' as pay_bgndate,
'#{pay_enddate}' as pay_enddate,
'#{bgndate}' as hz_bgndate,
'#{enddate}' as hz_enddate,
'#{fre_bgndate}' as fre_bgndate,
'#{fre_enddate}' as fre_enddate,
total.fchgagenidcode,
total.fchgagencode,
total.fchgagenname,

total.fitemidcode,
total.fitemname,
total.fitemcode,
total.fsubname,
total.fsubcode,
count(*) as ftotalnumber,
sum(total.famt) as ftotalamt,
sum(toDecimal32(total.fiscomplete,0)) as ftransfernumber,
sum(ftransferamt) as ftransferamt,
sum(toDecimal32(total.fisenter,0)) as freceivednumber,
sum(freceivedamt) as freceivedamt
from (select fp.fpaycode as fpaycode,
fp.fchgagenidcode as fchgagenidcode,
fp.fdate as fpaydate,
fp.ftransdate as fplandate,
fp.fenterdate as fenterdate,
case when ub.fpaycode <> '' then ub.fbankcode else fp.recbankcode end as fbankcode,
fp.fchgagencode as fchgagencode,
fp.fchgagenname as fchgagenname,
fp.fitemidcode as fitemidcode,
fp.fitemname as fitemname,
fp.fitemcode as fitemcode,
fp.fsubname as fsubname,
fp.fsubcode as fsubcode,
fp.famt as famt,
case when fp.famt<0 or fp.stats='9' or ub.fbalancedate <> '' then '1' else if(fp.isenter='','0',fp.isenter) end as fisenter,
case
when fp.isenter = '1'  or fp.famt<0 or fp.stats='9' or ub.fbalancedate <> '' then
fp.famt

else
toDecimal32(0,6)
end as freceivedamt,
fp.transno as ftransferno,
case when fp.famt<0 then '1' else if(fp.istransfer='','0',fp.istransfer) end as fiscomplete ,
case
when fp.istransfer = '1'  or fp.famt<0 then
fp.famt
else
toDecimal32(0,6)
end as ftransferamt,
fp.fsortno as fsortno
from (select
fpaycode,
fchgagenidcode,
fdate,
ftransdate,
fenterdate,
fchgagencode,
fchgagenname,
fitemidcode,
fitemname,
fitemcode,
fsubname,
fsubcode,
ifnull(fimamt,famt) as famt,
if('#{frecacct}'<>'' and '#{frecacct}'=ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', ftransrecbankcode, ftransrecbankcode_last) as recbankcode,
if(sfechz='0', fstats, fstats_last) as stats,
if(sfechz='0', fistransfer, fistransfer_last) as istransfer,
if(sfechz='0', fisenter, fisenter_last) as isenter,
if(sfechz='0', ftransno, ftransno_last) as transno,
if(sfechz='0', ftransrecacct, ftransrecacct_last) as transrecacct,
if(sfechz='0', ftransdate, ftransdate_last) as transdate,
if(sfechz='0', fenterdate, fenterdate_last) as enterdate,
fsortno
from fne_paybook_full_high
where  fpaycode not in (select fpaycode from une_paybook_paycode)
and fpaycode not in (select fpaycode from fne_unknown_capital_balance where fagenidcode in '${fagenidcode}'
and fagenidcode in (select fagenidcode from fab_agen where frgncode='${frgncode}' and fisfinal='1') )
and fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and transdate >= '${bgndate}'
and transdate <= '${enddate}'
and enterdate >= '${fre_bgndate}'
and enterdate <= '${fre_enddate}'
and fitemidcode = '${fitemidcode}'
and recbankcode = '${fbankcode}'
and transrecacct = '${frecacct}'
and ffundsnaturecode like '${ftype}%'
and fdatatag < '3'
union all
select
fpaycode,
fchgagenidcode,
fdate,
ftransdate,
freceiveddate,
fchgagencode,
fchgagenname,
fitemidcode,
fitemname,
fitemcode,
fsubname,
fsubcode,
ifnull(fimamt,famt) as famt,
'' as sfechz,
'' as frecbankcode,
fstats,
fistransfer,
fisenter,
ftransno,
ftransrecacct,
ftransdate,
fenterdate,
fsortno
from fne_paybook_full_high
where fpaycode not in (select fpaycode from une_paybook_paycode)
and fpaycode in (select fpaycode from fne_unknown_capital_balance where fagenidcode in '${fagenidcode}'
and fbankcode = '${fbankcode}'
and fagenidcode in (select fagenidcode from fab_agen where frgncode='${frgncode}' and fisfinal='1') )
and fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and ftransdate >= '${bgndate}'
and ftransdate <= '${enddate}'
and fitemidcode = '${fitemidcode}'
and freceiveddate>= '${fre_bgndate}'
and freceiveddate<= '${fre_enddate}'
and ffundsnaturecode like '${ftype}%'
and fdatatag < '3'

) fp
/*left join fne_refund_lock fr on fr.fdedpaycode=fp.fpaycode
left join fpf_payrefund fpr on fpr.fpaycode = fr.frefpaycode */
left join fne_unknown_capital_balance ub on ub.fpaycode = fp.fpaycode

where 1=1

) total

group by total.fchgagenidcode,
total.fchgagencode,
total.fchgagenname,
total.fitemidcode,
total.fitemname,
total.fitemcode,
total.fsubcode,
total.fsubname

union all

select
'#{pay_bgndate}' as pay_bgndate,
'#{pay_enddate}' as pay_enddate,
'#{bgndate}' as hz_bgndate,
'#{enddate}' as hz_enddate,
'#{fre_bgndate}' as fre_bgndate,
'#{fre_enddate}' as fre_enddate,
total.fchgagenidcode,
total.fchgagencode,
total.fchgagenname,

'' fitemidcode,
'' fitemname,
'' fitemcode,
'小计' fsubname,
'' fsubcode,
count(*) as ftotalnumber,
sum(total.famt) as ftotalamt,
sum(toDecimal32(total.fiscomplete,0)) as ftransfernumber,
sum(ftransferamt) as ftransferamt,
sum(toDecimal32(total.fisenter,0)) as freceivednumber,
sum(freceivedamt) as freceivedamt
from (select fp.fpaycode as fpaycode,

fp.fchgagenidcode as fchgagenidcode,
fp.fdate as fpaydate,
fp.ftransdate as fplandate,
fp.fenterdate as fenterdate,
case when ub.fpaycode <> '' then ub.fbankcode else fp.recbankcode end as fbankcode,
fp.fchgagencode as fchgagencode,
fp.fchgagenname as fchgagenname,
fp.fitemidcode as fitemidcode,
fp.fitemname as fitemname,
fp.fitemcode as fitemcode,
fp.fsubname as fsubname,
fp.fsubcode as fsubcode,
fp.famt as famt,
case when fp.famt<0 or fp.stats='9' or ub.fbalancedate <> '' then '1' else if(fp.isenter='','0',fp.isenter) end as fisenter,
case
when fp.isenter = '1'  or fp.famt<0 or fp.stats='9' or ub.fbalancedate <> '' then
fp.famt

else
toDecimal32(0,6)
end as freceivedamt,
fp.transno as ftransferno,
case when fp.famt<0 then '1' else if(fp.istransfer='','0',fp.istransfer) end as fiscomplete ,
case
when fp.istransfer = '1'  or fp.famt<0 then
fp.famt
else
toDecimal32(0,6)
end as ftransferamt,
fp.fsortno as fsortno
from (select
fpaycode,
fchgagenidcode,
fdate,
ftransdate,
fenterdate,
fchgagencode,
fchgagenname,
fitemidcode,
fitemname,
fitemcode,
fsubname,
fsubcode,
ifnull(fimamt,famt) as famt,
if('#{frecacct}'<>'' and '#{frecacct}'=ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', ftransrecbankcode, ftransrecbankcode_last) as recbankcode,
if(sfechz='0', fstats, fstats_last) as stats,
if(sfechz='0', fistransfer, fistransfer_last) as istransfer,
if(sfechz='0', fisenter, fisenter_last) as isenter,
if(sfechz='0', ftransno, ftransno_last) as transno,
if(sfechz='0', ftransrecacct, ftransrecacct_last) as transrecacct,
if(sfechz='0', ftransdate, ftransdate_last) as transdate,
if(sfechz='0', fenterdate, fenterdate_last) as enterdate,
fsortno
from fne_paybook_full_high
where  fpaycode not in (select fpaycode from une_paybook_paycode)
and fpaycode not in (select fpaycode from fne_unknown_capital_balance where fagenidcode in '${fagenidcode}'
and fagenidcode in (select fagenidcode from fab_agen where frgncode='${frgncode}' and fisfinal='1') )
and fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and transdate >= '${bgndate}'
and transdate <= '${enddate}'
and enterdate >= '${fre_bgndate}'
and enterdate <= '${fre_enddate}'
and fitemidcode = '${fitemidcode}'
and recbankcode = '${fbankcode}'
and transrecacct = '${frecacct}'
and ffundsnaturecode like '${ftype}%'

union all
select
fpaycode,
fchgagenidcode,
fdate,
ftransdate,
freceiveddate,
fchgagencode,
fchgagenname,
fitemidcode,
fitemname,
fitemcode,
fsubname,
fsubcode,
ifnull(fimamt,famt) as famt,
'' as sfechz,
'' as frecbankcode,
fstats,
fistransfer,
fisenter,
ftransno,
ftransrecacct,
ftransdate,
fenterdate,
fsortno
from fne_paybook_full_high
where fpaycode not in (select fpaycode from une_paybook_paycode)
and fpaycode in (select fpaycode from fne_unknown_capital_balance where fagenidcode in '${fagenidcode}'
and fbankcode = '${fbankcode}'
and fagenidcode in (select fagenidcode from fab_agen where frgncode='${frgncode}' and fisfinal='1') )
and fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and ftransdate >= '${bgndate}'
and ftransdate <= '${enddate}'
and fitemidcode = '${fitemidcode}'
and freceiveddate>= '${fre_bgndate}'
and freceiveddate<= '${fre_enddate}'
and ffundsnaturecode like '${ftype}%'

) fp
/*left join fne_refund_lock fr on fr.fdedpaycode=fp.fpaycode
left join fpf_payrefund fpr on fpr.fpaycode = fr.frefpaycode */
left join fne_unknown_capital_balance ub on ub.fpaycode = fp.fpaycode

where 1=1

) total
group by total.fchgagenidcode,
total.fchgagencode,
total.fchgagenname
)
order by fchgagencode||'-'||fitemcode

```

## 2.7 单位缴款统计明细表（查询库）-财政经常用-财政端

### 报表样式

![](report_images/image14.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收区划 | 否 | 默认为空，表示本级财政 | ${frgncode} | une_paybook_new.frgncode,fne_paybook_full_high.fchgrgncode,fab_agen.frgncode |
| 2 | 执收单位 | 否 | | ${fagenidcode} | fne_paybook_full_high.fchgagenidcode,fne_unknown_capital_balance.fagenidcode |
| 3 | 开票日期 | 否 | 包含起始日期和结束日期，默认为空 | ${bgndate},${enddate} | fne_paybook_full_high.ffilldate |
| 4 | 缴款日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${pay_bgndate},${pay_enddate} | fne_paybook_full_high.fdate |
| 5 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${fre_bgndate},${fre_enddate} | fne_paybook_full_high.enterdate |
| 6 | 收费项目 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_full_high.fitemidcode |
| 7 | 到账银行 | 否 | 默认为空 | ${bankcode} | fne_paybook_full_high.fpaybankcode |
| 8 | 资金性质 | 否 | 默认为空 | ${ftype} | fne_paybook_full_high.ffundsnaturecode |
| 9 | 缴款人帐号 | 否 | 默认为空 |  |  |
| 10 | 缴款人姓名 | 否 | 默认为空 | ${name} | une_paybook_new.fpayername,fne_paybook_full_high.fpayername |
| 11 | 缴款渠道 | 否 | 默认为空 | ${bankcode} | fne_paybook_full_high.fpaybankcode |
| 12 | 收款人帐号 | 否 | 默认为空 | ${frecacct} | fne_paybook_full_high.frecacct |
| 13 | 开票人 | 否 | 默认为空 | ${fauthor} | fne_paybook_full_high.fauthor |
| 14 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${p_bgndate},${p_enddate} | fne_paybook_full_high.ftransdate |
| 15 | 班级 | 否 | 默认为空，估计用于教育缴费 | ${class} | une_paybook_new.fcustom2 |
| 16 | 年级 | 否 | 默认为空，估计用于教育缴费 | ${grade} | une_paybook_new.fcustom1 |

### 报表语句
``` SQL
/*宁夏：单位缴款统计明细表*/
/*une_paybook_paycode线下退付*/
select fp.fpaycode as fpaycode,
fp.fpaybankname as fpaybankname,
fp.fchgagenidcode as fchgagenidcode,
fp.fchgagencode as fchgagencode,
fp.fchgagenname as fchgagenname,
fp.famt as famt,
case when fp.isenter = '1'  or fp.famt<0 or fp.stats='9' or ucb.fbalancedate <> '' then fp.famt else toDecimal32(0,6) end as freceivedamt,
fp.transdate as fplandate,
fp.fdate as fpaydate,
case when u.fpayername = ''  then fp.fpayername else u.fpayername end as fpayername,
fp.fauthor as fauthor,
u.fcustom1 as fcustom1,
u.fcustom2 as fcustom2,
u.fcustom3 as fcustom3,
u.fcustom4 as fcustom4,
fp.fitemname as fitemname,
fp.fitemcode as fitemcode,
fp.ffilldate as ffilldate,
u.fcomcbillbatchcode as fcomcbillbatchcode,
u.fbillname as fbillname,
u.fcomcbillno as fbillno,
fp.transdate as ftransdate,
fp.transno as ftransno,
case when ucb.fpaycode <> '' then fp.fdate else fp.enterdate end as enterdate,
u.fcheckcode as fcheckcode,
case when ucb.fpaycode <> '' then ucb.fbankcode else fp.transrecbankcode end as recbankcode,
case when ucb.fpaycode <> '' then uc.frecacctname else fp.transrecacctname end as frecacctname,
case when ucb.fpaycode <> '' then uc.frecacct else fp.transrecacct end as frecacct,
case when ucb.fpaycode <> '' then uc.frecacctbank else fp.frecacctbank end as frecacctbank,
fp.fsortno as fsortno
from (select fpaycode,
fpaybankname,
fchgagenidcode,
fchgagencode,
fchgagenname,
ifnull(fimamt,famt) as famt,
if('#{frecacct}'<>'' and '#{frecacct}'=ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', fisenter,  fisenter_last) as isenter,
if(sfechz='0', fstats, fstats_last) as stats,
if(sfechz='0', ftransdate, ftransdate_last) as transdate,
if(sfechz='0', ftransno, ftransno_last) as transno,
fdate,
fpayername,
fauthor,
fitemname,
fitemcode,
ffilldate,
freceiveddate,
if(sfechz='0', fenterdate, fenterdate_last) as enterdate,
if(sfechz='0', ftransrecbankcode, ftransrecbankcode_last) as transrecbankcode,
if(sfechz='0', ftransrecacctname, ftransrecacctname_last) as transrecacctname,
if(sfechz='0', ftransrecacct, ftransrecacct_last) as transrecacct,
frecacctbank,
fsortno
from fne_paybook_full_high
where fpaycode not in (select fpaycode from une_paybook_paycode)
and fpaycode not in (select fpaycode from fne_unknown_capital_balance where fagenidcode in '${fagenidcode}'
and fagenidcode in (select fagenidcode from fab_agen where frgncode='${frgncode}' and fisfinal='1') )
and fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and fpaybankcode = '${bankcode}'
and transdate >= '${p_bgndate}'
and transdate <= '${p_enddate}'
and fdate>= '${pay_bgndate}'
and fdate<= '${pay_enddate}'
and fdate = '${fpaydate}'
and ffilldate >= '${bgndate}'
and ffilldate <= '${enddate}'
and enterdate >= '${fre_bgndate}'
and enterdate <= '${fre_enddate}'
and fitemidcode = '${fitemidcode}'
and fauthor like '%${fauthor}%'
and transrecbankcode = '${fbankcode}'
and substr(ffundsnaturecode, 1, 1) = '${ftype}'
and fdatatag < '3'
union all
select fpaycode,
fpaybankname,
fchgagenidcode,
fchgagencode,
fchgagenname,
ifnull(fimamt,famt) as famt,
'' as sfechz,
fisenter,
fstats,
ftransdate,
ftransno,
freceiveddate,
fpayername,
fauthor,
fitemname,
fitemcode,
ffilldate,
freceiveddate,
fenterdate,
frecbankcode,
frecacctname,
frecacct,
frecacctbank,
fsortno
from fne_paybook_full_high
where fpaycode not in (select fpaycode from une_paybook_paycode)
and fpaycode in (select fpaycode from fne_unknown_capital_balance where fagenidcode in '${fagenidcode}'
and fbankcode = '${fbankcode}'
and fagenidcode in (select fagenidcode from fab_agen where frgncode='${frgncode}' and fisfinal='1') )
and fchgrgncode = '${frgncode}'
and fchgagenidcode in '${fagenidcode}'
and fpaybankcode = '${bankcode}'
and ftransdate >= '${p_bgndate}'
and ftransdate <= '${p_enddate}'
and fdate>= '${pay_bgndate}'
and fdate<= '${pay_enddate}'
and fdate = '${fpaydate}'
and ffilldate >= '${bgndate}'
and ffilldate <= '${enddate}'
and freceiveddate>= '${fre_bgndate}'
and freceiveddate<= '${fre_enddate}'
and fitemidcode = '${fitemidcode}'
and fauthor like '%${fauthor}%'
and substr(ffundsnaturecode, 1, 1) = '${ftype}'
and fdatatag < '3'
) fp
left join
( select fpaycode,fpayername,
fcustom1,
fcustom2,
fcustom3,
fcustom4,
fcomcbillbatchcode,
fbillname,
fcomcbillno,
fcheckcode
from une_paybook_new
where fagenidcode in '${fagenidcode}'
and frgncode = '${frgncode}'
and fcustom2 like '${class}%'
and fcustom1 like '${grade}%'
) u
on fp.fpaycode = u.fpaycode
/*left join fne_refund_lock fr on fr.fdedpaycode=fp.fpaycode --and pm.famt<0
left join fpf_payrefund fpr on fpr.fpaycode = fr.frefpaycode  */
left join fne_unknown_capital_balance ucb on ucb.fpaycode = fp.fpaycode
left join fne_unknown_capital uc on uc.fid = ucb.funknownfundsid

where 1=1
and (u.fpayername like '${name}%' or fp.fpayername like '${name}%')
and frecacct = '${frecacct}'
and u.fcustom2 like '${class}%'
and u.fcustom1 like '${grade}%'
order by fp.fchgagencode, fp.fpaycode, fp.fitemcode

```

## 2.8 财政端单位资金划转对账表（查询库）-财政端

### 报表样式

![](report_images/image17.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收区划 | 否 | 默认为空，表示本级财政 | ${fchgrgncode} | fpf_clear_transfer.fregioncode,fne_paybook_full_high.fregioncode |
| 2 | 执收单位 | 否 | | ${fchgagenidcode} | fne_unknown_capital_balance.fagenidcode,fne_paybook_full_high.fchgagenidcode |
| 3 | 缴款日期 | 否 | 包含起始日期和结束日期，默认为空 | ${pay_bgndate},${pay_enddate} | fne_paybook_full_high.fdate |
| 4 | 划转日期 | 是 | 包含起始日期和结束日期，默认为空 | ${trans_bgndate},${trans_enddate} | fne_paybook_full_high.transdate |
| 5 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${enter_bgndate},${enter_enddate} | fne_paybook_full_high.enterdate |
| 6 | 收款帐户类型 | 否 | 默认为空 | ${frecaccttype} | fab_acc.faccount |
| 7 | 结算渠道 | 否 | 默认为空 | ${fbankcode} | fne_paybook_full_high.fpaybankcode |
| 8 | 结算批次号 | 否 | 默认为空 | ${ftransno} | fne_paybook_full_high.ftransno |
| 9 | 到账银行 | 否 | 默认为空 | ${frecbankcode} | fne_paybook_full_high.recbankcode |
| 10 | 收款帐号 | 否 | 默认为空 | ${frecacct} | fne_paybook_full_high.recacct |

### 报表语句
``` SQL
/*宁夏：单位资金划转对账表（财政端）*/
select
'#{pay_bgndate}' as pay_bgndate,
'#{pay_enddate}' as pay_enddate,
p.transno as ftransno,
p.frecacctname as frecacctname,
p.recacct as frecacct,
case fa.facctype
when '0' then
'虚拟账户'
when '1' then
'财政专户'
when '2' then
'汇缴专户'
when '3' then
'待解缴科目'
when '4' then
'单位监管账户'
when '5' then
'国库账户'
when '7' then
'单位清分账户'
else
'其他'
end as frecaccttype,
p.frecbankname as frecbankname,
sum(p.famt) as famt,
p.fpaybankname as fpaybankname,
d.fname as fpaymentchannel,
p.transdate as ftransferdate,
p.enterdate as fenterdate,
p.fpaybankcode as fpaybankcode
from (select
if('#{frecacct}'<>'' and '#{frecacct}'= ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', ftransno, ftransno_last) as transno,
if(sfechz='0', ftransrecacctname, ftransrecacctname_last) as frecacctname,
if(sfechz='0', ftransrecacct, ftransrecacct_last) as recacct,
if(sfechz='0', ftransrecbankcode, ftransrecbankcode_last) as recbankcode,
if(sfechz='0', ftransrecbankname, ftransrecbankname_last) as frecbankname,
if(sfechz='0', ftransdate , ftransdate_last) as transdate,
if(sfechz='0', fenterdate , fenterdate_last) as enterdate,
fpaybankcode,
fpaybankname,
fpaymentchannel,
ifnull(fimamt, famt) as famt

from fne_paybook_full_high
where transdate >= '${trans_bgndate}'
and transdate <= '${trans_enddate}'
and enterdate >= '${enter_bgndate}'
and enterdate <= '${enter_enddate}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and fpaybankcode = '${fbankcode}'
and recacct = '${frecacct}'
and transno like '${ftransno}%'
and fchgagenidcode = '${fchgagenidcode}'
and recbankcode = '${frecbankcode}'
and fchgrgncode = '${fchgrgncode}'
and fpaycode not in (select fpaycode from fne_unknown_capital_balance)
union all
select
'' as sfechz,
fpaycode as ftransno,
frecacctname,
frecacct,
fpaybankcode as frecbankcode,
fpaybankname as frecbankname,
ftransdate,
freceiveddate,
fpaybankcode,
fpaybankname,
fpaymentchannel,
ifnull(fimamt, famt) as famt

from fne_paybook_full_high
where ftransdate >= '${trans_bgndate}'
and ftransdate <= '${trans_enddate}'
and freceiveddate >= '${enter_bgndate}'
and freceiveddate <= '${enter_enddate}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'

and fpaybankcode = '${fbankcode}'
and ftransno like '${ftransno}%'
and fchgagenidcode = '${fchgagenidcode}'
and fchgrgncode = '${fchgrgncode}'
and fpaycode in (
select fpaycode
from fne_unknown_capital_balance ucb
left join fne_unknown_capital uc
on uc.fid = ucb.funknownfundsid
where ucb.fagenidcode in '${fchgagenidcode}'
and ucb.fbankcode='${frecbankcode}'
and uc.frecacct='${frecacct}' )
) p
left join
(select fbatchno,fplandate,freceivedate
from fpf_clear_transfer
where fregioncode = '${fchgrgncode}'
and fplandate >= '${trans_bgndate}'
and fplandate <= '${trans_enddate}'
and freceivedate >= '${enter_bgndate}'
and freceivedate <= '${enter_enddate}'
and fiscomplete = '1'
) fp
on fp.fbatchno = p.transno
left join (select faccount,max(facctypecode) as facctype from fab_acc where fisfinal='1' group by faccount) fa
on fa.faccount = p.recacct
left join afa_res_dictitem d on p.fpaymentchannel = d.fcode and d.fdictcode = '132'

where fa.facctype = '${frecaccttype}'
group by ftransno,
frecacctname,
frecacct,
frecaccttype,
fpaybankname,
frecbankname,
fpaymentchannel,
ftransferdate,
fenterdate,
fpaybankcode
order by ftransferdate, fpaybankcode, frecacct

```

## 2.9 财政端单位资金划转对账明细表（查询库）-财政端

### 报表样式

![](report_images/image19.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收单位 | 否 | 默认为空，表示本级财政 | ${fchgagenidcode} | fne_unknown_capital_balance.fagenidcode,fne_paybook_full_high.fchgagenidcode |
| 2 | 项目名称 | 否 | | ${fitemidcode} | fne_paybook_full_high.fitemidcode |
| 3 | 缴款日期 | 否 | 包含起始日期和结束日期，默认为空 | ${pay_bgndate},${pay_enddate} | fne_paybook_full_high.fdate |
| 4 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${enter_bgndate},${enter_enddate} | fne_paybook_full_high.freceiveddate |
| 5 | 收款帐户类型 | 否 | 默认为空 | ${frecaccttype} | fab_acc.facctype |
| 6 | 结算渠道 | 否 | 默认为空 | ${fbankcode} | fne_unknown_capital_balance.fbankcode,fne_paybook_full_high.fbankcode |
| 7 | 结算批次号 | 否 | 默认为空 | ${ftransno} | fne_paybook_full_high.transno |
| 8 | 缴款人名称 | 否 | 默认为空 | ${fpayername} | une_paybook_new.fpayername |
| 9 | 收款银行名称 | 否 | 默认为空 | ${frecacctname} | fne_paybook_full_high.frecacctname |
| 10 | 电子缴款码 | 否 | 默认为空 | ${fpaycode} | fne_paybook_full_high.fpaycode |
| 11 | 收款人帐号 | 否 | 默认为空 | ${frecacct} | fne_unknown_capital_balance.frecacct,fne_paybook_full_high.recacct |
| 12 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${trans_bgndate},${trans_enddate} | fne_paybook_full_high.ftransdate |

### 报表语句
``` SQL
/*宁夏：单位资金划转对账明细表(财政)*/
select
p.fpaycode as fpaycode,
p.fchgagencode as fchgagencode,
p.fchgagenidcode as fchgagenidcode,
p.fchgagenname as fchgagenname,
u.fbillname as fbillname,
u.fcomcbillno as fbillno,
u.fpayername as fpayername,
u.fcustom1 as fcustom1,
u.fcustom2 as fcustom2,
u.fcustom3 as fcustom3,
u.fcustom4 as fcustom4,
p.frecacctname as frecacctname,
p.recacct as frecacct,
p.fitemcode as fitemcode,
p.fitemname as fitemname,
p.fimamt as famt,
p.transdate as ftransdate,
p.enterdate as fenterdate,
p.transno as ftransno

from (select
if('#{frecacct}'<>'' and '#{frecacct}'= ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', ftransno, ftransno_last) as transno,
if(sfechz='0', ftransrecacctname, ftransrecacctname_last) as frecacctname,
if(sfechz='0', ftransrecacct, ftransrecacct_last) as recacct,
if(sfechz='0', ftransrecbankcode, ftransrecbankcode_last) as recbankcode,
if(sfechz='0', ftransrecbankname, ftransrecbankname_last) as frecbankname,
if(sfechz='0', ftransdate , ftransdate_last) as transdate,
if(sfechz='0', fenterdate , fenterdate_last) as enterdate,
fpaybankcode,
fpaybankname,
fpaymentchannel,
fpaycode,
fchgagencode,
fchgagenidcode,
fchgagenname,
fitemcode,
fitemname,
ifnull(fimamt, famt) as fimamt

from fne_paybook_full_high
where transdate >= '${trans_bgndate}'
and transdate <= '${trans_enddate}'
and enterdate >= '${enter_bgndate}'
and enterdate <= '${enter_enddate}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and fpaybankcode = '${fbankcode}'
and recacct = '${frecacct}'
and transno like '${ftransno}%'
and fchgagenidcode = '${fchgagenidcode}'
and recbankcode = '${frecbankcode}'
and fchgrgncode = '${fchgrgncode}'
and fpaycode like '${fpaycode}%'
and fitemidcode = '${fitemidcode}'
and fpaycode not in (select fpaycode from fne_unknown_capital_balance)
union all
select
'' as sfechz,
fpaycode as ftransno,
frecacctname,
frecacct,
fpaybankcode as frecbankcode,
fpaybankname as frecbankname,
ftransdate,
freceiveddate,
fpaybankcode,
fpaybankname,
fpaymentchannel,
fpaycode,
fchgagencode,
fchgagenidcode,
fchgagenname,
fitemcode,
fitemname,
ifnull(fimamt, famt) as fimamt

from fne_paybook_full_high
where ftransdate >= '${trans_bgndate}'
and ftransdate <= '${trans_enddate}'
and freceiveddate >= '${enter_bgndate}'
and freceiveddate<= '${enter_enddate}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and fpaybankcode = '${fbankcode}'
and ftransno like '${ftransno}%'
and fchgagenidcode = '${fchgagenidcode}'
and fchgrgncode = '${fchgrgncode}'
and fpaycode like '${fpaycode}%'
and fitemidcode = '${fitemidcode}'
and fpaycode in (
select fpaycode
from fne_unknown_capital_balance ucb
left join fne_unknown_capital uc
on uc.fid = ucb.funknownfundsid
where ucb.fagenidcode in '${fchgagenidcode}'
and ucb.fbankcode='${frecbankcode}'
and uc.frecacct='${frecacct}' )
) p
left join
( select fpaycode,
fpayername,
fcustom1,
fcustom2,
fcustom3,
fcustom4,
fcomcbillbatchcode,
fbillname,
fcomcbillno,
fcheckcode
from une_paybook_new
where frgncode = '${fchgrgncode}'
and fagenidcode in '${fagenidcode}'
and fpayername like '${fpayername}%'
) u
on p.fpaycode = u.fpaycode
left join (select faccount,max(facctypecode) as facctype from fab_acc where fisfinal='1' group by faccount) fa
on fa.faccount = p.recacct

where fa.facctype = '${frecaccttype}'
and u.fpayername like '${fpayername}%'
order by ftransdate,fenterdate,fpaycode,fitemcode

```

## 2.10 单位端单位缴款统计汇总表（查询库）--单位端常用-单位端

### 报表样式

![](report_images/image22.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收单位 | 否 | 默认为空，表示本级财政 | ${fagenidcode} | uab_place.fagenidcode,fne_paybook_full_high.fagenidcode |
| 2 | 缴款日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${pay_bgndate},${pay_enddate} | fne_paybook_full_high.fdate |
| 3 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${fre_bgndate},${fre_enddate} | fne_paybook_full_high.enterdate |
| 5 | 收费项目 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_full_high.fitemidcode |
| 6 | 到账银行 | 否 | 默认为空 | ${fbankcode} | fne_paybook_full_high.recbankcode |
| 7 | 资金性质 | 否 | 默认为空 | ${ftype} | fne_paybook_full_high.ffundsnaturecode |
| 8 | 收款人帐号 | 否 | 默认为空 | ${frecacct} | fne_unknown_capital.frecacct,fne_paybook_full_high.transrecacct |
| 9 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${bgndate},${enddate} | fne_paybook_full_high.ftransdate |

### 报表语句
``` SQL
select
'#{pay_bgndate}' as pay_bgndate,
'#{pay_enddate}' as pay_enddate,
'#{bgndate}' as hz_bgndate,
'#{enddate}' as hz_enddate,
'#{fre_bgndate}' as fre_bgndate,
'#{fre_enddate}' as fre_enddate,
total.fchgagenidcode,
total.fchgagencode,
total.fchgagenname,

total.fitemidcode,
total.fitemname,
total.fitemcode,
total.fsubname,
total.fsubcode,
count(*) as ftotalnumber,
sum(total.famt) as ftotalamt,
sum(toDecimal32(total.fiscomplete,0)) as ftransfernumber,
sum(ftransferamt) as ftransferamt,
sum(toDecimal32(total.fisenter,0)) as freceivednumber,
sum(freceivedamt) as freceivedamt
from (select fp.fpaycode as fpaycode,

fp.fchgagenidcode as fchgagenidcode,
fp.fdate as fpaydate,
fp.ftransdate as fplandate,
fp.fenterdate as freceivedate, --划转到账时间
case when ub.fpaycode <> '' then ub.fbankcode else fp.recbankcode end as fbankcode,
fp.fchgagencode as fchgagencode,
fp.fchgagenname as fchgagenname,
fp.fitemidcode as fitemidcode,
fp.fitemname as fitemname,
fp.fitemcode as fitemcode,
fp.fsubname as fsubname,
fp.fsubcode as fsubcode,
fp.famt as famt,
case when fp.famt<0 or fp.stats='9' or ub.fbalancedate <> '' then '1' else if(fp.isenter='','0',fp.isenter) end as fisenter,
case
when fp.isenter = '1'  or fp.famt<0 or fp.stats='9' or ub.fbalancedate <> '' then
fp.famt

else
toDecimal32(0,6)
end as freceivedamt,
fp.transno as ftransferno,
case when fp.famt<0 then '1' else if(fp.istransfer='','0',fp.istransfer) end as fiscomplete ,
case
when fp.istransfer = '1'  or fp.famt<0 then
fp.famt
else
toDecimal32(0,6)
end as ftransferamt,
fp.fsortno as fsortno
from (select
'1' as ftype,
fpaycode,
fchgagenidcode,
fdate,
ftransdate,
fenterdate, --划转到账时间
fchgagencode,
fchgagenname,
fitemidcode,
fitemname,
fitemcode,
fsubname,
fsubcode,
ifnull(fimamt,famt) as famt,
if('#{frecacct}'<>'' and '#{frecacct}'=ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', ftransrecbankcode, ftransrecbankcode_last) as recbankcode,
if(sfechz='0', fstats, fstats_last) as stats,
if(sfechz='0', fistransfer, fistransfer_last) as istransfer,
if(sfechz='0', fisenter, fisenter_last) as isenter,
if(sfechz='0', ftransno, ftransno_last) as transno,
if(sfechz='0', ftransrecacct, ftransrecacct_last) as transrecacct,
if(sfechz='0', ftransdate, ftransdate_last) as transdate,
if(sfechz='0', fenterdate, fenterdate_last) as enterdate,
fsortno
from fne_paybook_full_high
where  fpaycode not in (select fpaycode from une_paybook_paycode)
and fchgagenidcode in '${fagenidcode}'
and fplaceid in (
select distinct up.fid
from uab_place up
left join uab_place_user upu
on up.fid = upu.fplaceid
where up.fagenidcode='${fagenidcode}'
and (upu.fuserid = '${getUser("ID")}'  or  (select fismanage from uab_place_user where fuserid = '${getUser("ID")}' )=1
or (select count(1) from uab_place_user where fuserid = '${getUser("ID")}' )=0 ))
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and transdate >= '${bgndate}'
and transdate <= '${enddate}'
and enterdate >= '${fre_bgndate}'
and enterdate <= '${fre_enddate}'
and fitemidcode = '${fitemidcode}'
and recbankcode = '${fbankcode}'
and transrecacct = '${frecacct}'
and substr(ffundsnaturecode, 1, 1) = '${ftype}'
and fpaycode not in (select fpaycode from fne_unknown_capital_balance)
union all
select
'2' as ftype,
fpaycode,
fchgagenidcode,
fdate,
ftransdate,
freceiveddate, --划转到账时间
fchgagencode,
fchgagenname,
fitemidcode,
fitemname,
fitemcode,
fsubname,
fsubcode,
ifnull(fimamt,famt) as famt,
'' as sfechz,
'' as frecbankcode,
fstats,
fistransfer,
fisenter,
ftransno,
ftransrecacct,
ftransdate,
fenterdate,
fsortno
from fne_paybook_full_high
where fchgagenidcode in '${fagenidcode}'
and fplaceid in (
select distinct up.fid
from uab_place up
left join uab_place_user upu
on up.fid = upu.fplaceid
where up.fagenidcode='${fagenidcode}'
and (upu.fuserid = '${getUser("ID")}'  or  (select fismanage from uab_place_user where fuserid = '${getUser("ID")}' )=1
or (select count(1) from uab_place_user where fuserid = '${getUser("ID")}' )=0 ))
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and ftransdate >= '${bgndate}'
and ftransdate <= '${enddate}'
and fitemidcode = '${fitemidcode}'
and freceiveddate>= '${fre_bgndate}'
and freceiveddate<= '${fre_enddate}'
and substr(ffundsnaturecode, 1, 1) = '${ftype}'
and fpaycode in (select fpaycode from fne_unknown_capital_balance ucb left join fne_unknown_capital uc on uc.fid = ucb.funknownfundsid   where ucb.fagenidcode in '${fagenidcode}' and ucb.fbankcode='${fbankcode}' and uc.frecacct='${frecacct}' )
) fp
/* left join fne_refund_lock fr on fr.fdedpaycode=fp.fpaycode
left join fpf_payrefund fpr on fpr.fpaycode = fr.frefpaycode */
left join fne_unknown_capital_balance ub on ub.fpaycode = fp.fpaycode

where 1=1

) total

group by total.fchgagenidcode,
total.fchgagencode,
total.fchgagenname,
total.fitemidcode,
total.fitemname,
total.fitemcode,
total.fsubcode,
total.fsubname

```

## 2.11 单位端单位缴款统计明细表（查询库）--单位端常用-单位端

### 报表样式

![](report_images/image25.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收单位 | 否 | 默认为空，表示本级财政 | ${fagenidcode} | uab_place.fagenidcode,fne_paybook_full_high.fchgagenidcode |
| 2 | 开票日期 | 否 | 包含起始日期和结束日期，默认为空 | ${bgndate},${enddate} | fne_paybook_full_high.ffilldate |
| 3 | 缴款日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${pay_bgndate},${pay_enddate} | fne_paybook_full_high.fdate |
| 4 | 收费项目 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_full_high.fitemidcode |
| 5 | 开票人 | 否 | 默认为空 | ${fauthor} | fne_paybook_full_high.fauthor |
| 6 | 缴款渠道 | 否 | 默认为空 | ${bankcode} | fne_paybook_full_high.fpaybankcode |
| 7 | 到账银行 | 否 | 默认为空 | ${fbankcode} | fne_paybook_full_high.transrecbankcode |
| 8 | 资金性质 | 否 | 默认为空 | ${ftype} | fne_paybook_full_high.ffundsnaturecode |
| 9 | 收款人帐号 | 否 | 默认为空 | ${frecacct} | fne_paybook_full_high.frecacct |
| 10 | 缴款人姓名 | 否 | 默认为空 | ${name} | une_paybook_new.fpayername,fne_paybook_full_high.fpayername |
| 11 | 班级 | 否 | 默认为空 | ${class} | une_paybook_new.fcustom2 |
| 12 | 年级 | 否 | 默认为空 | ${grade} | une_paybook_new.fcustom1 |
| 13 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${p_bgndate},${p_enddate} | fne_paybook_full_high.transdate |

### 报表语句
``` SQL
/*宁夏：单位缴款统计明细表*/
select fp.fpaycode as fpaycode,
fp.fpaybankname as fpaybankname,
fp.fchgagencode as fchgagencode,
fp.fchgagenname as fchgagenname,
fp.famt as famt,
case when fp.isenter = '1'  or fp.famt<0 or fp.stats='9' or ucb.fbalancedate <> '' then fp.famt else toDecimal32(0,6) end as freceivedamt,
fp.transdate as fplandate,
fp.fdate as fpaydate,
case when u.fpayername = ''  then fp.fpayername else u.fpayername end as fpayername,
fp.fauthor as fauthor,
u.fcustom1 as fcustom1,
u.fcustom2 as fcustom2,
u.fcustom3 as fcustom3,
u.fcustom4 as fcustom4,
fp.fitemname as fitemname,
fp.fitemcode as fitemcode,
fp.ffilldate as ffilldate,
u.fcomcbillbatchcode as fcomcbillbatchcode,
u.fbillname as fbillname,
u.fcomcbillno as fbillno,
fp.transdate as ftransdate,
fp.transno as ftransno,
case when ucb.fpaycode <> '' then fp.fdate else fp.enterdate end as enterdate,
u.fcheckcode as fcheckcode,
case when ucb.fpaycode <> '' then ucb.fbankcode else fp.transrecbankcode end as recbankcode,
case when ucb.fpaycode <> '' then uc.frecacctname else fp.transrecacctname end as frecacctname,
case when ucb.fpaycode <> '' then uc.frecacct else fp.transrecacct end as frecacct,
case when ucb.fpaycode <> '' then uc.frecacctbank else fp.frecacctbank end as frecacctbank,
fp.fsortno as fsortno
from (select fpaycode,
fpaybankname,
fchgagencode,
fchgagenname,
ifnull(fimamt,famt) as famt,
if('#{frecacct}'<>'' and '#{frecacct}'=ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', fisenter,  fisenter_last) as isenter,
if(sfechz='0', fstats, fstats_last) as stats,
if(sfechz='0', ftransdate, ftransdate_last) as transdate,
if(sfechz='0', ftransno, ftransno_last) as transno,
fdate,
fpayername,
fauthor,
fitemname,
fitemcode,
ffilldate,
freceiveddate,
if(sfechz='0', fenterdate, fenterdate_last) as enterdate,
if(sfechz='0', ftransrecbankcode, ftransrecbankcode_last) as transrecbankcode,
if(sfechz='0', ftransrecacctname, ftransrecacctname_last) as transrecacctname,
if(sfechz='0', ftransrecacct, ftransrecacct_last) as transrecacct,
frecacctbank,
fsortno
from fne_paybook_full_high
where  fpaycode not in (select fpaycode from une_paybook_paycode)
and fchgagenidcode in '${fagenidcode}'
and fplaceid in (
select distinct up.fid
from uab_place up
left join uab_place_user upu
on up.fid = upu.fplaceid
where up.fagenidcode='${fagenidcode}'
and (upu.fuserid = '${getUser("ID")}'  or  (select fismanage from uab_place_user where fuserid = '${getUser("ID")}' )=1
or (select count(1) from uab_place_user where fuserid = '${getUser("ID")}' )=0 ))
and fpaybankcode = '${bankcode}'
and transdate >= '${p_bgndate}'
and transdate <= '${p_enddate}'
and fdate>= '${pay_bgndate}'
and fdate<= '${pay_enddate}'
and fdate = '${fpaydate}'
and ffilldate >= '${bgndate}'
and ffilldate <= '${enddate}'
and enterdate >= '${fre_bgndate}'
and enterdate <= '${fre_enddate}'
and fitemidcode = '${fitemidcode}'
and fauthor like '%${fauthor}%'
and transrecbankcode = '${fbankcode}'
and substr(ffundsnaturecode, 1, 1) = '${ftype}'
and fpaycode not in (select fpaycode from fne_unknown_capital_balance)
union all
select fpaycode,
fpaybankname,
fchgagencode,
fchgagenname,
ifnull(fimamt,famt) as famt,
'' as sfechz,
fisenter,
fstats,
ftransdate,
ftransno,
freceiveddate,
fpayername,
fauthor,
fitemname,
fitemcode,
ffilldate,
freceiveddate,
fenterdate,
frecbankcode,
frecacctname,
frecacct,
frecacctbank,
fsortno
from fne_paybook_full_high
where fchgagenidcode in '${fagenidcode}'
and fplaceid in (
select distinct up.fid
from uab_place up
left join uab_place_user upu
on up.fid = upu.fplaceid
where up.fagenidcode='${fagenidcode}'
and (upu.fuserid = '${getUser("ID")}'  or  (select fismanage from uab_place_user where fuserid = '${getUser("ID")}' )=1
or (select count(1) from uab_place_user where fuserid = '${getUser("ID")}' )=0 ))
and fpaybankcode = '${bankcode}'
and ftransdate >= '${p_bgndate}'
and ftransdate <= '${p_enddate}'
and fdate>= '${pay_bgndate}'
and fdate<= '${pay_enddate}'
and fdate = '${fpaydate}'
and ffilldate >= '${bgndate}'
and ffilldate <= '${enddate}'
and freceiveddate>= '${fre_bgndate}'
and freceiveddate<= '${fre_enddate}'
and fitemidcode = '${fitemidcode}'
and fauthor like '%${fauthor}%'
and substr(ffundsnaturecode, 1, 1) = '${ftype}'
and fpaycode in (select fpaycode from fne_unknown_capital_balance where fagenidcode in '${fagenidcode}' and fbankcode='${fbankcode}' )
) fp
left join
( select fpaycode,fpayername,
fcustom1,
fcustom2,
fcustom3,
fcustom4,
fcomcbillbatchcode,
fbillname,
fcomcbillno,
fcheckcode
from une_paybook_new
where fagenidcode in '${fagenidcode}'
and fcustom2 like '${class}%'
and fcustom1 like '${grade}%'
) u
on fp.fpaycode = u.fpaycode
/* left join fne_refund_lock fr on fr.fdedpaycode=fp.fpaycode --and pm.famt<0
left join fpf_payrefund fpr on fpr.fpaycode = fr.frefpaycode  */
left join fne_unknown_capital_balance ucb on ucb.fpaycode = fp.fpaycode
left join fne_unknown_capital uc on uc.fid = ucb.funknownfundsid

where 1=1
and (u.fpayername like '${name}%' or fp.fpayername like '${name}%')
and frecacct = '${frecacct}'
and u.fcustom2 like '${class}%'
and u.fcustom1 like '${grade}%'
order by fp.fchgagencode, fp.fpaycode, fp.fitemcode

```

## 2.12 单位端单位资金划转对账表（查询库）-单位端

### 报表样式

![](report_images/image28.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收单位 | 否 | 默认为空，表示本级财政 | ${fchgagenidcode} | fne_unknown_capital_balance.fagenidcode,fne_paybook_full_high.fchgagenidcode |
| 2 | 缴款日期 | 否 | 包含起始日期和结束日期，默认为空 | ${pay_bgndate},${pay_enddate} | fne_paybook_full_high.fdate |
| 3 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${enter_bgndate},${enter_enddate} | fne_paybook_full_high.freceiveddate |
| 4 | 收款账户类型 | 否 | 默认为空 | ${frecaccttype} | fab_acc.facctype |
| 5 | 结算渠道 | 否 | 默认为空 | ${fbankcode} | fne_paybook_full_high.fpaybankcode |
| 6 | 结算批次号 | 否 | 默认为空 | ${ftransno} | fne_paybook_full_high.transno |
| 7 | 收款人帐号 | 否 | 默认为空 | ${frecacct} | fne_unknown_capital.frecacct,fne_paybook_full_high.recacct |
| 8 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${trans_bgndate},${trans_enddate} | fne_paybook_full_high.transdate |


### 报表语句
``` SQL
/*宁夏：单位资金划转对账表（单位端）*/
select
'#{pay_bgndate}' as pay_bgndate,
'#{pay_enddate}' as pay_enddate,
p.transno as FTRANSNO,
'' as FMEMO,
p.frecacctname as FRECACCTNAME,
p.recacct as FRECACCT,
case fa.facctype
when '0' then
'虚拟账户'
when '1' then
'财政专户'
when '2' then
'汇缴专户'
when '3' then
'待解缴科目'
when '4' then
'单位监管账户'
when '5' then
'国库账户'
when '7' then
'单位清分账户'
else
'其他'
end as FRECACCTTYPE,
p.frecbankname as FRECBANKNAME,
sum(p.famt) as FAMT,
p.fpaybankname as FPAYBANKNAME,
d.fname as FPAYMENTCHANNEL,
p.transdate as FTRANSFERDATE,
p.enterdate as FENTERDATE,
p.fpaybankcode as FPAYBANKCODE
from (select
if('#{frecacct}'<>'' and '#{frecacct}'= ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', ftransno, ftransno_last) as transno,
if(sfechz='0', ftransrecacctname, ftransrecacctname_last) as frecacctname,
if(sfechz='0', ftransrecacct, ftransrecacct_last) as recacct,
if(sfechz='0', ftransrecbankcode, ftransrecbankcode_last) as recbankcode,
if(sfechz='0', ftransrecbankname, ftransrecbankname_last) as frecbankname,
if(sfechz='0', ftransdate , ftransdate_last) as transdate,
if(sfechz='0', fenterdate , fenterdate_last) as enterdate,
fpaybankcode,
fpaybankname,
fpaymentchannel,
ifnull(fimamt, famt) as famt

from fne_paybook_full_high
where transdate >= '${trans_bgndate}'
and transdate <= '${trans_enddate}'
and enterdate >= '${enter_bgndate}'
and enterdate <= '${enter_enddate}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and fpaybankcode = '${fbankcode}'
and recacct = '${frecacct}'
and transno like '${ftransno}%'
and fchgagenidcode = '${fchgagenidcode}'
and recbankcode = '${frecbankcode}'
and fchgrgncode = '${fchgrgncode}'
and fpaycode not in (select fpaycode from fne_unknown_capital_balance)
union all
select
'' as sfechz,
fpaycode as ftransno,
frecacctname,
frecacct,
fpaybankcode as frecbankcode,
fpaybankname as frecbankname,
ftransdate,
freceiveddate,
fpaybankcode,
fpaybankname,
fpaymentchannel,
ifnull(fimamt, famt) as famt

from fne_paybook_full_high
where ftransdate >= '${trans_bgndate}'
and ftransdate <= '${trans_enddate}'
and freceiveddate >= '${enter_bgndate}'
and freceiveddate <= '${enter_enddate}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and fpaybankcode = '${fbankcode}'
and ftransno like '${ftransno}%'
and fchgagenidcode = '${fchgagenidcode}'
and fchgrgncode = '${fchgrgncode}'
and fpaycode in (
select fpaycode
from fne_unknown_capital_balance ucb
left join fne_unknown_capital uc
on uc.fid = ucb.funknownfundsid
where ucb.fagenidcode in '${fchgagenidcode}'
and ucb.fbankcode='${frecbankcode}'
and uc.frecacct='${frecacct}' )
) p
left join
(select fbatchno,fplandate,freceivedate
from fpf_clear_transfer
where fregioncode = '${fchgrgncode}'
and fplandate >= '${trans_bgndate}'
and fplandate <= '${trans_enddate}'
and freceivedate >= '${enter_bgndate}'
and freceivedate <= '${enter_enddate}'
and fiscomplete = '1'
) fp
on fp.fbatchno = p.transno
left join (select faccount,max(facctypecode) as facctype from fab_acc where fisfinal='1' group by faccount) fa
on fa.faccount = p.recacct
left join afa_res_dictitem d on p.fpaymentchannel = d.fcode and d.fdictcode = '132'

where fa.facctype = '${frecaccttype}'
group by FTRANSNO,
FMEMO,
FRECACCTNAME,
FRECACCT,
FRECACCTTYPE,
FPAYBANKNAME,
FRECBANKNAME,
FPAYMENTCHANNEL,
FTRANSFERDATE,
FENTERDATE,
FPAYBANKCODE
order by FTRANSFERDATE, FPAYBANKCODE, FRECACCT

```

## 2.13 单位端单位资金划转对账明细表（查询库）-单位端

### 报表样式

![](report_images/image31.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收单位 | 否 | 默认为空，表示本级财政 | ${fchgagenidcode} | fne_unknown_capital_balance.fagenidcode,fne_paybook_full_high.fchgagenidcode |
| 2 | 项目名称 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_full_high.fitemidcode |
| 3 | 缴款日期 | 否 | 包含起始日期和结束日期，默认为空 | ${pay_bgndate},${pay_enddate} | fne_paybook_full_high.fdate |
| 4 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${trans_bgndate},${trans_enddate} | fne_paybook_full_high.transdate |
| 5 | 收款账户类型 | 否 | 默认为空 | ${frecaccttype} | fab_acc.facctype |
| 6 | 结算渠道 | 否 | 默认为空 | ${fbankcode} | fne_paybook_full_high.fpaybankcode |
| 7 | 结算批次号 | 否 | 默认为空 | ${ftransno} | fne_paybook_full_high.transno |
| 8 | 缴款人名称 | 否 | 默认为空 | ${fpayername} | une_paybook_new.fpayername |
| 9 | 收款银行名称 | 否 | 默认为空 |  |  |
| 10 | 电子缴款码 | 否 | 默认为空 | ${fpaycode} | fne_paybook_full_high.fpaycode |
| 11 | 收款人帐号 | 否 | 默认为空 | ${frecacct} | fne_unknown_capital.frecacct,fne_paybook_full_high.recacct |


### 报表语句
``` SQL
/*宁夏：单位资金划转对账明细表(财政)*/
select
p.fpaycode as FPAYCODE,
p.fchgagencode as FCHGAGENCODE,
p.fchgagenidcode as FCHGAGENIDCODE,
p.fchgagenname as FCHGAGENNAME,
u.fbillname as FBILLNAME,
u.fcomcbillno as FBILLNO,
u.fpayername as FPAYERNAME,
u.fcustom1 as FCUSTOM1,
u.fcustom2 as FCUSTOM2,
u.fcustom3 as FCUSTOM3,
u.fcustom4 as FCUSTOM4,
p.frecacctname as FRECACCTNAME,
p.recacct as FRECACCT,
p.fitemcode as FITEMCODE,
p.fitemname as FITEMNAME,
p.fimamt as FAMT,
p.transdate as FTRANSDATE,
p.enterdate as FENTERDATE,
p.transno as FTRANSNO

from (select
if('#{frecacct}'<>'' and '#{frecacct}'= ftransrecacct_last, '1', '0') as sfechz,  --是否二次划转
if(sfechz='0', ftransno, ftransno_last) as transno,
if(sfechz='0', ftransrecacctname, ftransrecacctname_last) as frecacctname,
if(sfechz='0', ftransrecacct, ftransrecacct_last) as recacct,
if(sfechz='0', ftransrecbankcode, ftransrecbankcode_last) as recbankcode,
if(sfechz='0', ftransrecbankname, ftransrecbankname_last) as frecbankname,
if(sfechz='0', ftransdate , ftransdate_last) as transdate,
if(sfechz='0', fenterdate , fenterdate_last) as enterdate,
fpaybankcode,
fpaybankname,
fpaymentchannel,
fpaycode,
fchgagencode,
fchgagenidcode,
fchgagenname,
fitemcode,
fitemname,
ifnull(fimamt, famt) as fimamt

from fne_paybook_full_high
where transdate >= '${trans_bgndate}'
and transdate <= '${trans_enddate}'
and enterdate >= '${enter_bgndate}'
and enterdate <= '${enter_enddate}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and fpaybankcode = '${fbankcode}'
and recacct = '${frecacct}'
and transno like '${ftransno}%'
and fchgagenidcode = '${fchgagenidcode}'
and recbankcode = '${frecbankcode}'
and fchgrgncode = '${fchgrgncode}'
and fpaycode like '${fpaycode}%'
and fitemidcode = '${fitemidcode}'
and fpaycode not in (select fpaycode from fne_unknown_capital_balance)
union all
select
'' as sfechz,
fpaycode as ftransno,
frecacctname,
frecacct,
fpaybankcode as frecbankcode,
fpaybankname as frecbankname,
ftransdate,
freceiveddate,
fpaybankcode,
fpaybankname,
fpaymentchannel,
fpaycode,
fchgagencode,
fchgagenidcode,
fchgagenname,
fitemcode,
fitemname,
ifnull(fimamt, famt) as fimamt

from fne_paybook_full_high
where ftransdate >= '${trans_bgndate}'
and ftransdate <= '${trans_enddate}'
and freceiveddate>= '${enter_bgndate}'
and freceiveddate<= '${enter_enddate}'
and fdate >= '${pay_bgndate}'
and fdate <= '${pay_enddate}'
and fpaybankcode = '${fbankcode}'
and ftransno like '${ftransno}%'
and fchgagenidcode = '${fchgagenidcode}'
and fchgrgncode = '${fchgrgncode}'
and fpaycode like '${fpaycode}%'
and fitemidcode = '${fitemidcode}'
and fpaycode in (
select fpaycode
from fne_unknown_capital_balance ucb
left join fne_unknown_capital uc
on uc.fid = ucb.funknownfundsid
where ucb.fagenidcode in '${fchgagenidcode}'
and ucb.fbankcode='${frecbankcode}'
and uc.frecacct='${frecacct}' )
) p
left join
( select fpaycode,
fpayername,
fcustom1,
fcustom2,
fcustom3,
fcustom4,
fcomcbillbatchcode,
fbillname,
fcomcbillno,
fcheckcode
from une_paybook_new
where frgncode = '${fchgrgncode}'
and fagenidcode in '${fagenidcode}'
and fpayername like '${fpayername}%'
) u
on p.fpaycode = u.fpaycode
left join (select faccount,max(facctypecode) as facctype from fab_acc where fisfinal='1' group by faccount) fa
on fa.faccount = p.recacct

where fa.facctype = '${frecaccttype}'
and u.fpayername like '${fpayername}%'

order by FTRANSDATE,FENTERDATE,FPAYCODE,FITEMCODE

```

## 2.14 财政开票明细表（查询库）-财政端

### 报表样式

![](report_images/image33.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 开票日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${date_bgn},${date_end} | une_cbill_high.fdate,une_writeoff_new.fdate |
| 2 | 区划 | 否 | 默认为空 | ${region} | une_cbill_high.frgncode,une_writeoff_new.frgncode |
| 3 | 用票单位 | 否 | 默认为空 | ${fagenidcode} | une_cbill_high.fagenidcode,une_writeoff_new.fagenidcode |
| 4 | 开票点 | 否 | 默认为空 | ${fplaceid} | une_cbill_high.fplaceid,une_writeoff_new.fplaceid |
| 5 | 票据种类 | 否 | 默认为空 | ${fbillid} | une_cbill_high.fbillid,une_writeoff_new.foldbillid |
| 6 | 票据代码 | 否 | 默认为空 | ${fbatchcode} | une_cbill_high.fbillbatchcode,une_writeoff_new.foldbillbatchcode |
| 7 | 票号 | 否 | 默认为空 | ${fbillno} | une_cbill_high.fbillno,une_writeoff_new.foldbillno |
| 8 | 缴款人 | 否 | 默认为空 | ${fpayername} | une_cbill_high.fpayername |
| 9 | 编制人 | 否 | 默认为空 | ${fauthor} | une_cbill_high.fauthor |
| 10 | 备注 | 否 | 默认为空 | ${fmemo} | une_cbill_high.fmemo |

### 报表语句
``` SQL
select c.fagenname as fagenname,
c.fplacename as fplacename,
c.fdate as fdate,
c.fbillcode as fbillcode,
c.fbillname as fbillname,
c.fbillbatchcode as fbillbatchcode,
c.fbillno as fbillno,
c.fpayername as fpayername,
--if(b.finvoicemode='1',if(c.frelatedbillno<>'','√',''),'') as fisprint,
if(c.frelatedbillno<>'','√','') as fisprint,
if(w.fbillno<>'','√','') as fiskhp,
c.frelatedbillno as fprintbillno,
w.fbillno as felectbillno,
c.fcheckcode as fcheckcode,
c.fexternalid as fexternalid,
c.fitemcode as fitemstdcode,
c.fitemname as fitemname,
c.funits as funits,
c.fnumber as fnumber,
c.fstd as fstd,
c.famt as famt,
c.fmemo as fmemo,
if(c.fstate='1', '正常', '作废') as fstate,
if(c.fbillcode='4002' or c.fbillcode='4012',c.ficustom5,c.ficustom4) as itemmemo,
c.fauthor as fauthor,
b.finvoicemode as finvoicemode
from (select
fagenname,
fplacename,
fdate,
fbillid,
fbillcode,
fbillname,
fbillbatchcode,
fbillno,
fpayername,
frelatedbillno,
frelatedbillno,
fcheckcode,
fexternalid,
fitemcode,
fitemname,
funits ,
fnumber,
fstd,
famt,
fmemo,
fstate,
fauthor,
fpid,
ficustom4,
ficustom5
from une_cbill_high
where fbustype <> '5'
and fplaceid = '${fplaceid}'
and fbillid = '${fbillid}'
and fbillbatchcode = '${fbatchcode}'
and fbillno = '${fbillno}'
and fpayername = '${fpayername}'
and fauthor like '%${fauthor}%'
and fmemo like '%${fmemo}%'
and fagenidcode = '${fagenidcode}'
and frgncode = '${region}'
and fdate >= '${date_bgn}'
and fdate <= '${date_end}'
) c
left join
(select fbillno,foldbillid,foldbillbatchcode,foldbillno,fstate
from une_writeoff_new
where frgncode = '${region}'
and fagenidcode in '${fagenidcode}'
and fplaceid = '${fplaceid}'
and fdate >= '${date_bgn}'
and foldbillid = '${fbillid}'
and foldbillbatchcode = '${fbatchcode}'
and foldbillno = '${fbillno}'
and fstate = '1'
) w
on c.fbillid = w.foldbillid
and c.fbillbatchcode = w.foldbillbatchcode
and c.fbillno = w.foldbillno
left join fab_bill b
on c.fbillid = b.fid
order by c.fdate desc,c.fbillno desc

```

## 2.15 单位开票明细表（查询库）-单位端

### 报表样式

![](report_images/image35.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 开票日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${date_bgn},${date_end} | une_cbill_high.fdate,une_writeoff_new.fdate |
| 2 | 用票单位 | 否 | 默认为空 | ${fagenidcode} | une_cbill_high.fagenidcode,une_writeoff_new.fagenidcode,uab_place.fagenidcode |
| 3 | 开票点 | 否 | 默认为空 | ${fplaceid} | une_cbill_high.fplaceid,une_writeoff_new.fplaceid,uab_place.fplaceid |
| 4 | 票据种类 | 否 | 默认为空 | ${fbillid} | une_cbill_high.fbillid |
| 5 | 票据代码 | 否 | 默认为空 | ${fbatchcode} | une_cbill_high.fbillbatchcode |
| 6 | 票号 | 否 | 默认为空 | ${fbillno} | une_cbill_high.fbillno |
| 7 | 收费项目 | 否 | 默认为空 | ${fitemidcode} | une_cbill_high.fitemidcode |
| 8 | 项目标准 | 否 | 默认为空 | ${fitemstdidcode} | une_cbill_high.fitemstdidcode |
| 9 | 缴款人 | 否 | 默认为空 | ${fpayername} | une_cbill_high.fpayername |
| 10 | 编制人 | 否 | 默认为空 | ${fauthor} | une_cbill_high.fauthor |
| 11 | 票号段 | 否 | 包含起始票号和结束票号，默认为空 | ${fbillno_bgn},${fbillno_end} | une_cbill_high.fbillno |
| 12 | 开票方式 | 否 | 默认为空 | ${finvoicecode} | fab_bill.finvoicemodecode |
| 13 | 票据状态 | 否 | 默认为空 | ${fstate} | une_cbill_high.fstate |
| 14 | 业务流水号 | 否 | 默认为空 | ${fexternalid} | une_cbill_high.fexternalid |
| 15 | 标志 | 否 | 默认为空 | ${bz} | une_cbill_high.fisprint,une_cbill_high.fiskhp |
| 16 | 备注 | 否 | 默认为空 | ${fmemo} | une_cbill_high.fmemo |

### 报表语句
``` SQL
select  distinct c.fagenname as fagenname,
c.fplacename as fplacename,
c.fdate as fdate,
b.fbillcode as fbillcode,
b.fbillname as fbillname,
c.fbillbatchcode as fbillbatchcode,
c.fbillno as fbillno,
c.fpayername as fpayername,
if(b.finvoicemodecode='1',if(c.frelatedbillno<>'','√',''),'') as fisprint,
if(w.fbillno<>'','√','') as fiskhp,
multiIf(fisprint='√','1',fiskhp='√','2','3') bz,
c.frelatedbillno as fprintbillno,
w.fbillno as felectbillno,
c.fcheckcode as fcheckcode,
c.fexternalid as fexternalid,
c.fitemcode as fitemstdcode,
c.fitemname as fitemname,
c.funits as funits,
c.fnumber as fnumber,
c.fstd as fstd,
c.famt as famt,
c.fmemo as fmemo,
if(c.fstate='2', '作废', '正常') as fstate,
c.fauthor as fauthor,
b.finvoicemodecode as fbilltype,
c.fpid as id
from (select fdate,fagencode,fagenname,fplacecode,fplacename,fbillid,fbillcode,fbillname,fbillbatchcode,fbillno,fpayername,
frelatedbillno,fcheckcode,fexternalid,fitemcode,fitemname,funits,fnumber,fstd,famt,fmemo,fstate,fauthor,fpid
from une_cbill_high
where fisinvoice='1'
and fbillid = '${fbillid}'
and fbillbatchcode = '${fbatchcode}'
and fbillno = '${fbillno}'
and fbillno >= '${fbillno_bgn}'
and fbillno <= '${fbillno_end}'
and fitemidcode = '${fitemidcode}'
and fitemstdidcode = '${fitemstdidcode}'
and fstate = '${fstate}'
and fexternalid = '${fexternalid}'
and fmemo like '%${fmemo}%'
and fpayername like '%${fpayername}%'
and fauthor = '${fauthor}'
and fplaceid = '${fplaceid}'
and fplaceid in (
select distinct up.fid
from uab_place up
left join uab_place_user upu
on up.fid = upu.fplaceid
where up.fagenidcode='${fagenidcode}'
and (upu.fuserid = '${getUser("ID")}'  or  (select fismanage from uab_place_user where fuserid = '${getUser("ID")}' )=1
or (select count(1) from uab_place_user where fuserid = '${getUser("ID")}' )=0 ))
and frgncode  = '${frgncode}'
and fagenidcode = '${fagenidcode}'
and fdate >= '${date_bgn}'
and fdate <= '${date_end}'

) c
left join (select foldbillid,foldbillbatchcode,foldbillno,max(fbillno) fbillno
from une_writeoff_new
where fstate ='1'
and fdate>='${date_bgn}'
and fplaceid = '${fplaceid}'
and frgncode  = '${frgncode}'
and fagenidcode = '${fagenidcode}'
group by foldbillid,foldbillbatchcode,foldbillno
) w
on c.fbillid = w.foldbillid
and c.fbillbatchcode = w.foldbillbatchcode
and c.fbillno = w.foldbillno
-- and w.fstate = '1'
left join fab_bill b
on b.fid = c.fbillid
where 1=1 and bz = '${bz}'
and b.finvoicemodecode = '${finvoicecode}'
order by c.fdate desc, c.fagencode, c.fplacecode, b.fbillcode, c.fbillbatchcode, c.fbillno desc

```


# 3 生产库报表
该部分报表数据从实时生产库中读取（Oracle）


## 3.1 吴忠市非税收入电子票据开票明细凭证-单位端

### 报表样式
![](report_images/image38.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 记账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${date_bgn},${date_end} | fpf_clear_transfer.freceivedate |
| 2 | 单位 | 否 | | ${fagenidcode} | fne_paybook.fchgagenidcode |
| 3 | 票据种类 | 否 | | ${fbillid} | une_paybook.fbillid |
| 4 | 收费项目 | 否 | | ${fitemidcode} | fne_paybook_item.fitemidcode |
| 5 | 到账银行 | 否 | | ${fbankcode} | fpf_clear_transfer.frecacctbankcode |

### 报表语句
``` SQL
/*非税收入电子票据开票明细凭证*/
select c.fbillbatchcode,
b.fbillcode,
b.fbillname,
c.faccagenname as fagenname,
c.fbillno,
c.fdate,
pi.famt as ftotalamt,
c.fauthor,
decode(c.fstate, '2', '是', '否') as fstate
from fne_paybook p
left join fne_paybook_item pi
on pi.fpid = p.fid
left join une_paybook c
on p.fpaycode = c.fpaycode
left join fne_funddivide f
on f.fpaybooksubid = pi.fid
left join FNE_Collect_To_Transfer tf on f.fcollectid = tf.FTRANSCOLLECTID
left join fpf_clear_transfer fp
on fp.fbatchno = tf.ftransferno
and fp.fiscomplete = '1'
left join fab_bill b
on c.fbillid = b.fid

where p.fchgrgncode like '6403%'
and p.fchgagenidcode = '${fagenidcode}'
and c.fbillid = '${fbillid}'
and pi.fitemidcode = '${fitemidcode}'
and fp.frecacctbankcode = '${fbankcode}'
and fp.freceivedate >= '${date_bgn}'
and fp.freceivedate <= '${date_end}'
order by c.fbillbatchcode, b.fbillcode, c.fagencode

```


## 3.2 吴忠市非税收入电子票据开票汇总凭证-财政端

### 报表样式

![](report_images/image40.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 开票日期 | 否 | 包含起始日期和结束日期，默认为空 | ${kpdate_bgn},${kpdate_end} | fne_paybook.ffilldate |
| 2 | 记账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${date_bgn},${date_end} | fpf_clear_transfer.freceivedate |
| 3 | 区划 | 否 | | ${frgncode} | fne_paybook.fchgrgncode |
| 4 | 单位 | 否 | | ${fagenidcode} | fne_paybook.fchgagenidcode |
| 5 | 票据种类 | 否 | | ${fbillid} | une_paybook.fbillid |
| 6 | 收费项目 | 否 | | ${fitemcode} | fne_paybook_item.fitemidcode |
| 7 | 到账银行 | 否 | | ${fbankcode} | fpf_clear_transfer.frecacctbankcode |
| 8 | 是否生成缴款书 | 否 | | ${ispaybook} | une_paybook.fpaycode |

### 报表语句
``` SQL
/*非税收入电子票据开票汇总凭证*/
select p.fchgagenname fagenname, --单位名称
up.fbillbatchcode, --票据代码
b.fbillcode, --票据编码
b.fbillname, --票据名称
count( p.fpaycode) as ftotalnumber, --合计份数
count(decode((select nvl(max(c.fstate),'1') from une_cbill c where c.fpaycode=p.fpaycode and rownum=1), '1', p.fpaycode, '')) as fnumber, --开票份数
count(decode((select nvl(max(c.fstate),'1') from une_cbill c where c.fpaycode=p.fpaycode and rownum=1), '2', p.fpaycode, '')) as finvalidnumber, --作废份数
sum(pi.famt) as ftotalamt, --合计
sum(decode((select nvl(max(c.frecmode),'1') from une_cbill c where c.fpaycode=p.fpaycode and rownum=1), '1', pi.famt, 0)) as famt1, --现金
sum(decode((select nvl(max(c.frecmode),'1')  from une_cbill c where c.fpaycode=p.fpaycode and rownum=1), '2', pi.famt, 0)) as famt2, --转账
sum(decode((select nvl(max(c.frecmode),'1')  from une_cbill c where c.fpaycode=p.fpaycode and rownum=1), '3', pi.famt, 0)) as famt3 --其他
from fne_paybook p
left join fne_paybook_item pi
on pi.fpid = p.fid
left join une_paybook up
on p.fpaycode = up.fpaycode
left join fne_funddivide f
on f.fpaybooksubid = pi.fid
left join FNE_Collect_To_Transfer tf on f.fcollectid = tf.FTRANSCOLLECTID
left join fpf_clear_transfer fp
on fp.fbatchno = tf.ftransferno
and fp.fiscomplete = '1'
left join fab_bill b
on up.fbillid = b.fid
where  pi.fitemidcode = '${fitemcode}'
and up.fbillid = '${fbillid}'
and fp.frecacctbankcode = '${fbankcode}'
and fp.freceivedate >= '${date_bgn}'
and fp.freceivedate <= '${date_end}'
and p.fchgagenidcode = '${fagenidcode}'
and p.fchgrgncode = '${frgncode}'
and p.ffilldate >= '${kpdate_bgn}'
and p.ffilldate <= '${kpdate_end}'
and decode(up.fpaycode,null,'0','1') = '${ispaybook}'
group by p.fchgagencode,
p.fchgagenname,
up.fbillbatchcode,
b.fbillcode,
b.fbillname
order by p.fchgagencode, up.fbillbatchcode, b.fbillcode

```

## 3.3 非税收入收支对账表-财政端

### 报表样式

![](report_images/image42.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${date_bgn},${date_end} | fab_acc_monitor.fdate |
| 2 | 区划 | 否 | 默认为空 | ${frgncode} | afa_auth_region.fcode |
| 3 | 银行 | 否 | 默认为空 | ${fbankcode} | fab_acc_monitor.fbankcode |

### 报表语句
``` SQL
select t.*,(case when famt_ye=famt_qm then '√' else '×' end) as sfyz, famt_qm - famt_ye as famt_ce from
(select a.fdate,
a.fbankcode,
b.fname as fbankname,
nvl(qc.famt_qc,0) as famt_qc,
nvl(a.famt_sr,0)  as famt_sr,
nvl(a.famt_gt,0)  as famt_gt,
nvl(a.famt_zfb,0) as famt_zfb,
nvl(a.famt_wx,0)  as famt_wx,
nvl(a.famt_wm,0)  as famt_wm,
nvl(a.famt_zc,0)  as famt_zc,
nvl(a.famt_gk,0)  as famt_gk,
nvl(a.famt_zh,0)  as famt_zh,
nvl(a.famt_ye,0)  as famt_ye,
nvl(qc.famt_qc,0) + nvl(a.famt_sr,0) - nvl(a.famt_zc,0) as famt_qm
from
(--日期银行收支汇总
select
fam.fdate,
fam.fbankcode,
sum(case when fam.fpaymenttype = '1' then fam.famt else 0 end) as famt_sr,    --收入合计
sum(case when fam.fpaymenttype = '1' and f.fpaychannel = '11' then fam.famt else 0 end) as famt_gt,  --柜台收入
sum(case when fam.fpaymenttype = '1' and f.fpaychannel = '51' then fam.famt else 0 end) as famt_zfb, --支付宝收入
sum(case when fam.fpaymenttype = '1' and f.fpaychannel = '52' then fam.famt else 0 end) as famt_wx,  --微信收入
sum(case when fam.fpaymenttype = '1' and f.fpaychannel in ('11','51,''52') then 0 else fam.famt end) as famt_wm,  --未名收入
sum(case when fam.fpaymenttype != '1' then fam.famt else 0 end) as famt_zc,   --支出合计
sum(case when fam.fpaymenttype != '1' and f.fbgtstyle = '1'  then fam.famt else 0 end) as famt_gk,   --缴入国库
sum(case when fam.fpaymenttype != '1' and f.fbgtstyle != '1' then fam.famt else 0 end) as famt_zh,   --缴入专户
sum(fam.fsurplus) as famt_ye  --余额
from fab_acc_monitor fam
left join fne_clear_reconciled rc
on fam.fbankcode = rc.fbankcode and fam.fserialno = rc.ffundsserialno
left join fne_collect_to_transfer c
on rc.fbatchno = c.ftransferno
left  join fne_funddivide f
on f.fcollectid = c.ftranscollectid
left  join v_fab_acc v
on v.Faccount = fam.frecacct
and v.FisFinal = '1'
left  join afa_auth_region r
on r.id = fam.frgnid
left join fab_subject fs
on fs.fsubcode = f.fsubcode and fs.fyear = f.fyear

where r.fcode = '${frgncode}'
and fam.fbankcode = '${fbankcode}'
and fam.fdate >= '${date_bgn}'
and fam.fdate <= '${date_end}'
and decode(f.fbgtstyle,'1','1','2') = '${fbgtstyle}'

group by fam.fdate,
fam.fbankcode
) a
left join fpf_bank b on a.fbankcode = b.fcode
left join ( --上期余额
select to_char(to_date(m.fdate,'yyyy-mm-dd')+1,'yyyy-mm-dd') as fdate,m.fbankcode, sum(fsurplus) as famt_qc
from fab_acc_monitor m
join afa_auth_region r on r.id = m.frgnid
where r.fcode = '${frgncode}'
and fdate >= to_char(to_date('#{date_bgn}','yyyy-mm-dd')-1,'yyyy-mm-dd')
and fdate <= to_char(to_date('#{date_end}','yyyy-mm-dd')-1,'yyyy-mm-dd')
group by fdate,fbankcode
) qc
on a.fdate = qc.fdate and a.fbankcode = qc.fbankcode
) t   order by    t. fdate

```

## 3.4 纳入预算收费统计表-财政端

### 报表样式
![](report_images/image44.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 日期 | 是 | 包含起始日期和结束日期，默认为本月 | \${date_bgn},${date_end} | fab_acc_monitor.fdate |
| 2 | 区划 | 否 | 默认为空 | ${frgncode} | afa_auth_region.fcode |
| 3 | 单位 | 否 | 默认为空 | ${fagencode} | fne_funddivide.fchgagencode |
| 4 | 预算科目 | 否 | 默认为空 | ${fsubcode} | fne_funddivide.fsubcode |
| 5 | 资金性质 | 否 | 默认为空 | ${fbgtstyle} | fne_funddivide.fbgtstyle |

### 报表语句
``` SQL
with tmp as (
--单位科目收支汇总
select f.fchgagenidcode,
fs.fsubcode,
fs.fsubname,
sum(case when fam.fpaymenttype = '1' then fam.famt else 0 end) as famt_sr,  --收入
sum(case when fam.fpaymenttype = '1' then 0 else fam.famt end) as famt_zc   --支出

from fab_acc_monitor fam
join fne_clear_reconciled rc
on fam.fbankcode = rc.fbankcode and fam.fserialno = rc.ffundsserialno
join fne_collect_to_transfer c
on rc.fbatchno = c.ftransferno
join fne_funddivide f
on f.fcollectid = c.ftranscollectid
join v_fab_acc v
on v.Faccount = fam.frecacct
and v.FisFinal = '1'
join afa_auth_region r
on r.id = fam.frgnid
join fab_subject fs
on fs.fsubcode = f.fsubcode and fs.fyear = f.fyear

where r.fcode = '${frgncode}'
and f.fchgagencode in '${fagencode}'
and f.fsubcode = '${fsubcode}'
and fam.fdate >= '${date_bgn}'
and fam.fdate <= '${date_end}'
and decode(f.fbgtstyle,'1','1','2') = '${fbgtstyle}'

group by f.fchgagenidcode,
fs.fsubcode,
fs.fsubname
)

select a.fagencode||'-'||t.fsubcode as xh,
'' as fagencode,
'' as fagenname,
t.fsubcode,
t.fsubname,
0 as famt_qc,
nvl(t.famt_sr,0) as famt_sr,
nvl(t.famt_zc,0) as famt_zc,
0 as famt_qm
from tmp t
join fab_agen a on t.fchgagenidcode = a.fagenidcode and a.fisfinal = '1'

union all
--按单位汇总
select a.fagencode as xh,
a.fagencode,
a.fagenname,
'',
'',
nvl(qc.fsurplus,0) as famt_qc,
nvl(t.famt_sr,0) as famt_sr,
nvl(t.famt_zc,0) as famt_zc,
nvl(qc.fsurplus,0) + nvl(t.famt_sr,0) - nvl(t.famt_zc,0) as famt_qm
from (select fchgagenidcode,sum(famt_sr) as famt_sr,sum(famt_zc) as famt_zc from tmp group by fchgagenidcode) t
join fab_agen a on t.fchgagenidcode = a.fagenidcode and a.fisfinal = '1'
left join (
select v.fagenidcode,m.fsurplus
from fab_acc_monitor m
join v_fab_acc v
on v.Faccount = m.frecacct
and v.FisFinal = '1'
where (fagenacct,fdate) in (select fagenacct,max(fdate) as fdate from fab_acc_monitor where fdate < '#{date_bgn}' group by fagenacct)
) qc
on t.fchgagenidcode = qc.fagenidcode
union all
--按主管部门汇总
select aa.fagencode as xh,
aa.fagencode,
aa.fagenname,
'',
'',
sum(nvl(qc.fsurplus,0)) as famt_qc,
sum(nvl(t.famt_sr,0)) as famt_sr,
sum(nvl(t.famt_zc,0)) as famt_zc,
sum(nvl(qc.fsurplus,0) + nvl(t.famt_sr,0) - nvl(t.famt_zc,0)) as famt_qm
from (select fchgagenidcode,sum(famt_sr) as famt_sr,sum(famt_zc) as famt_zc from tmp group by fchgagenidcode) t
join fab_agen a on t.fchgagenidcode = a.fagenidcode and a.fisfinal = '1'
join fab_agen aa on aa.fagencode = substr(a.fagencode,1,3) and aa.fisfinal = '1'
left join (
select v.fagenidcode,m.fsurplus
from fab_acc_monitor m
join v_fab_acc v
on v.Faccount = m.frecacct
and v.FisFinal = '1'
where (fagenacct,fdate) in (select fagenacct,max(fdate) as fdate from fab_acc_monitor where fdate < '#{date_bgn}' group by fagenacct)
) qc
on t.fchgagenidcode = qc.fagenidcode
group by aa.fagencode,aa.fagenname
order by xh

```

## 3.5 吴忠市非税收入电子票据汇总记账凭证-财政端

### 报表样式

![](report_images/image46.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 记账日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${date_bgn},${date_end} | fpf_clear_transfer.freceivedate |
| 2 | 区划 | 否 | 默认为空 | ${frgncode} | fne_paybook.fchgrgncode |
| 3 | 单位 | 否 | 默认为空 | ${fagenidcode} | fne_paybook.fchgagenidcode |
| 4 | 到账银行 | 否 | 默认为空 | ${fbankcode} | fpf_clear_transfer.frecacctbankcode |
| 5 | 收费项目 | 否 | 默认为空 | ${fitemcode} | fne_paybook_item.fitemidcode |
| 6 | 资金性质 | 否 | 默认为空 | ${ffundsortcode} | fne_funddivide.ffundsort |

### 报表语句
``` SQL
/*非税收入电子票据汇总记账凭证*/
select p.fchgagenname as fagenname,
pi.fitemname,
pi.fsubcode,
pi.fsubname,
count(p.fpaycode) as fconfirmnum,
sum(f.fimamt) as fconfirmamt,
count(decode(p.freceiveddate, '', '', p.fpaycode)) as freceivenum,
sum(decode(p.freceiveddate, '', 0, f.fimamt)) as freceiveamt
from fne_paybook p
join fne_paybook_item pi
on p.fid = pi.fpid
left join fne_funddivide f
on f.fpaybooksubid = pi.fid
left join fne_collect_to_transfer tf
on tf.ftranscollectid = f.fcollectid
left join fpf_clear_transfer fp
on fp.fbatchno = tf.ftransferno
and fp.fiscomplete = '1'

where pi.fitemidcode = '${fitemcode}'
and p.fchgrgncode = '${frgncode}'
and fp.freceivedate >= '${date_bgn}'
and fp.freceivedate <= '${date_end}'
and p.fchgagenidcode = '${fagenidcode}'
and fp.frecacctbankcode = '${fbankcode}'
and f.ffundsort = '${ffundsortcode}'
group by p.fchgagencode,
p.fchgagenname,
pi.fitemcode,
pi.fitemname,
pi.fsubcode,
pi.fsubname
order by p.fchgagencode, pi.fitemcode, pi.fsubcode

```

## 3.6 吴忠市非税收入电子票据明细记账凭证-财政端

### 报表样式

![](report_images/image48.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 记账日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${date_bgn},${date_end} | fpf_clear_transfer.freceivedate |
| 2 | 区划 | 否 | 默认为空 | ${frgncode} | fne_paybook.fchgrgncode |
| 3 | 单位 | 否 | 默认为空 | ${fagenidcode} | fne_paybook.fchgagenidcode |
| 4 | 到账银行 | 否 | 默认为空 | ${fbankcode} | fpf_clear_transfer.frecacctbankcode |
| 5 | 收费项目 | 否 | 默认为空 | ${fitemcode} | fne_paybook_item.fitemidcode |

### 报表语句
``` SQL
/*吴忠市非税收入电子票据明细记账凭证*/
select p.fchgagenname as fagenname,
u.fpayername as fpayername,
pi.fitemname,
pi.fitemcode,
pi.famt,
dict.fname,
p.fpaydate as fconfirmdate,
p.freceiveddate as freceivedate
from fne_paybook p
join fne_paybook_item pi
on p.fid = pi.fpid
left join une_paybook u
on u.fpaycode = p.fpaycode
left join fne_funddivide f
on f.fpaybooksubid = pi.fid
left join FNE_Collect_To_Transfer tf on f.fcollectid = tf.FTRANSCOLLECTID
left join fpf_clear_transfer fp
on fp.fbatchno = tf.ftransferno
and fp.fiscomplete = '1'

left join afa_res_dictitem dict
on p.fpaymentchannel = dict.fcode
and dict.fdictcode = '132'
where pi.fitemidcode =  '${fitemcode}'
and p.fchgrgncode like '6403%'
and p.fchgrgncode = '${frgncode}'
and fp.freceivedate >= '${date_bgn}'
and fp.freceivedate <= '${date_end}'
and p.fchgagenidcode = '${fagenidcode}'
and fp.frecacctbankcode = '${fbankcode}'
order by p.fchgagencode, pi.fitemcode

```


## 3.7 缴款统计分析报表-财政端

### 报表样式

![](report_images/image50.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 开票日期 | 否 | 包含起始日期和结束日期，默认为本月 | ${date_bgn},${date_end} | une_paybook.fdate |
| 2 | 缴款日期 | 否 | 包含起始日期和结束日期，默认为本月 | ${bgndate},${enddate} | une_paybook.fconfirmdate |
| 3 | 单位 | 否 | 默认为空 | ${agen} | une_paybook.faccagenidcode |
| 4 | 收费项目 | 否 | 默认为空 | ${item} | une_paybook_item.fitemidcode |
| 5 | 缴款码 | 否 | 默认为空 | ${pookcode} | une_paybook.fpaycode |
| 6 | 年级 | 否 | 默认为空 | ${grade} | une_paybook.fcustom1 |
| 7 | 班级 | 否 | 默认为空 | ${class} | une_paybook.fcustom2 |
| 8 | 姓名 | 否 | 默认为空 | ${xinming} | une_paybook.fpayername |
| 9 | 身份证号 | 否 | 默认为空 | ${sfzno} | une_paybook.fcustom3 |
| 10 | 学籍号 | 否 | 默认为空 | ${xuejino} | une_paybook.fcustom4 |
| 11 | 缴款状态 | 否 | 默认为空 | ${state} | une_paybook.fstate |
| 12 | 是否换开纸质票 | 否 | 默认为空 | ${hstate} | une_paybook.fstate |

### 报表语句
``` SQL
select *
from (
select t.fpaycode,--缴款码
t.fplacename,--开票点名称
t.fauthor,--开票人
to_char(to_date((substr(t.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss') fdate,--开票日期
c.fbillno as fbillno,--电子票号
t.fcompbillno frelatedno,
decode(t.fstate,1,'未缴款',2,'作废',3,'已缴款确认',4,'电子转纸质票据','','未缴款') fstate,--缴款状态
case when   t.fcompbillno is not NULL then '已开纸质票据'
when t.fcompbillno is NULL  then '未开纸质票据'
end  hstate,--换开状态
to_char(to_date((substr(uc.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss')fconfirmdate,--缴款日期
t.fpayername,--付款人全称
t.fpayerno,--付款人账号
t.fcustom1,--年级
t.fcustom2,--班级
t.fcustom3,--身份证号
t.fcustom4,--学籍号
ti.fitemcode,--收费项目编码
ti.fitemname,  -- 收费项目名称
ti.famt
from  une_paybook t
left join une_paybook_item ti on t.fid=ti.fpid
left join une_paybook_confirm uc
on uc.fpaycode = t.fpaycode
left join une_cbill c on c.fpaycode=t.fpaycode and c.ffinsignature = '1'
where t.fstate='3'
and t.fconfirmdate>='${bgndate}' and t.fconfirmdate<='${enddate}'
and t.fdate>='${date_bgn}' and t.fdate<='${date_end}'
and t.fpaycode like '%${pookcode}'
and t.faccagenidcode='${agen}'
and t.fcustom1='${grade}'
and t.fcustom2='${class}'
and nvl(t.fstate,1)='${state}'
and ti.fitemidcode='${item}'
and t.fpayername like '%${xinming}%'
and t.fcustom3 like '${sfzno}%'
and t.fcustom4 like '${xuejino}%'

union all

select t.fpaycode,--缴款码
t.fplacename,--开票点名称
t.fauthor,--开票人
to_char(to_date((substr(t.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss') fdate,--开票日期
'' as fbillno,--电子票号
'' frelatedno,--相关纸质票号
decode(t.fstate,1,'未缴款',2,'作废',3,'已缴款确认',4,'电子转纸质票据','','未缴款') fstate,
'未开纸质票据'hstate,
to_char(to_date((substr(uc.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss')fconfirmdate,--缴款日期
t.fpayername,--付款人全称
t.fpayerno,--付款人账号
t.fcustom1,--年级
t.fcustom2,--班级
t.fcustom3,--身份证号
t.fcustom4,--学籍号
ti.fitemcode,--收费项目编码
ti.fitemname,  -- 收费项目名称
ti.famt
from une_paybook t
left join une_paybook_item ti on t.fid=ti.fpid
left join une_paybook_confirm uc
on uc.fpaycode = t.fpaycode
where t.fstate<>'3'
and t.fdate>='${date_bgn}' and t.fdate<='${date_end}'
and t.fpaycode like '%${pookcode}'
and t.faccagenidcode='${agen}'
and t.fcustom1='${grade}'
and t.fcustom2='${class}'
and nvl(t.fstate,1)='${state}'
and ti.fitemidcode='${item}'
and t.fpayername like '%${xinming}%'
and t.fcustom3 like '${sfzno}%'
and t.fcustom4 like '${xuejino}%'
)where hstate = '${hstate}'

```

## 3.8 缴款统计分析明细报表-单位端

### 报表样式

![](report_images/image52.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 开票日期 | 否 | 包含起始日期和结束日期，默认为本月 | ${date_bgn},${date_end} | une_paybook.fdate |
| 2 | 缴款日期 | 否 | 包含起始日期和结束日期，默认为本月 | ${bgndate},${enddate} | une_paybook.fconfirmdate |
| 3 | 单位 | 否 | 默认为空 | ${agen} | une_paybook.faccagenidcode |
| 4 | 收费项目 | 否 | 默认为空 | ${item} | une_paybook_item.fitemidcode |
| 5 | 缴款码 | 否 | 默认为空 | ${pookcode} | une_paybook.fpaycode |
| 6 | 年级 | 否 | 默认为空 | ${grade} | une_paybook.fcustom1 |
| 7 | 班级 | 否 | 默认为空 | ${class} | une_paybook.fcustom2 |
| 8 | 姓名 | 否 | 默认为空 | ${xinming} | une_paybook.fpayername |
| 9 | 身份证号 | 否 | 默认为空 | ${sfzno} | une_paybook.fcustom3 |
| 10 | 学籍号 | 否 | 默认为空 | ${xuejino} | une_paybook.fcustom4 |
| 11 | 缴款状态 | 否 | 默认为空 | ${state} | une_paybook.fstate |
| 12 | 是否换开纸质票 | 否 | 默认为空 | ${hstate} | une_paybook.fstate |

### 报表语句
``` SQL
select *
from (
select t.fpaycode,--缴款码
t.fplacename,--开票点名称
t.fauthor,--开票人
--to_date(substr(t.fcreatetime,0,14),'YYYY-MM-DD HH24:MI:SS ') fdate,--开票日期
to_char(to_date((substr(t.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss') fdate,--开票日期
--t.fdate,--开票日期

t.fbillno,--电子票号
t.fcompbillno frelatedno,
--decode(c.fbustype,2,c.frelatedbillno,'') frelatedno,--相关纸质票号
decode(t.fstate,1,'未缴款',2,'作废',3,'已缴款确认',4,'电子转纸质票据','','未缴款') fstate,--缴款状态
case when   t.fcompbillno is not NULL then '已开纸质票据'
when t.fcompbillno is NULL  then '未开纸质票据'
end  hstate,--换开状态
--t.fconfirmdate,--缴款日期
to_char(to_date((substr(uc.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss')fconfirmdate,--缴款日期
t.fpayername,--付款人全称
t.fpayerno,--付款人账号
t.fcustom1,--年级
t.fcustom2,--班级
t.fcustom3,--身份证号
t.fcustom4,--学籍号
ti.fitemcode,--收费项目编码
ti.fitemname,  -- 收费项目名称
ti.famt
from  une_paybook t
left join une_paybook_item ti on t.fid=ti.fpid
left join une_paybook_confirm uc
on uc.fpaycode = t.fpaycode
-- left join une_cbill c on c.fpaycode=t.fpaycode and c.ffinsignature = '1'
where t.fstate='3'
and t.fconfirmdate>='${bgndate}' and t.fconfirmdate<='${enddate}'
and t.fdate>='${date_bgn}' and t.fdate<='${date_end}'
and t.fpaycode like '%${pookcode}'
and t.faccagenidcode='${agen}'
and t.fcustom1='${grade}'
and t.fcustom2='${class}'
and nvl(t.fstate,1)='${state}'
and ti.fitemidcode='${item}'
and t.fpayername like '%${xinming}%'
and t.fcustom3 like '${sfzno}%'
and t.fcustom4 like '${xuejino}%'
union all
select t.fpaycode,--缴款码
t.fplacename,--开票点名称
t.fauthor,--开票人
--to_date(substr(t.fcreatetime,0,14),'YYYY-MM-DD HH24:MI:SS ') fdate,--开票日期
to_char(to_date((substr(t.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss') fdate,--开票日期
--t.fdate,--开票日期
'' as fbillno,--电子票号
'' frelatedno,--相关纸质票号
decode(t.fstate,1,'未缴款',2,'作废',3,'已缴款确认',4,'电子转纸质票据','','未缴款') fstate,--缴款状态
/*case when   t.fcompbillno is not NULL then '已开纸质票据'
when t.fcompbillno is NULL  then '未开纸质票据'
end  hstate,--换开状态*/
'未开纸质票据'hstate,
--t.fconfirmdate,--缴款日期
to_char(to_date((substr(uc.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss')fconfirmdate,--缴款日期
t.fpayername,--付款人全称
t.fpayerno,--付款人账号
t.fcustom1,--年级
t.fcustom2,--班级
t.fcustom3,--身份证号
t.fcustom4,--学籍号
ti.fitemcode,--收费项目编码
ti.fitemname,  -- 收费项目名称
ti.famt
from une_paybook t
left join une_paybook_item ti on t.fid=ti.fpid
left join une_paybook_confirm uc
on uc.fpaycode = t.fpaycode
where t.fstate<>'3'
and t.fdate>='${date_bgn}' and t.fdate<='${date_end}'
and t.fpaycode like '%${pookcode}'
and t.faccagenidcode='${agen}'
and t.fcustom1='${grade}'
and t.fcustom2='${class}'
and nvl(t.fstate,1)='${state}'
and ti.fitemidcode='${item}'
and t.fpayername like '%${xinming}%'
and t.fcustom3 like '${sfzno}%'
and t.fcustom4 like '${xuejino}%'
)where hstate = '${hstate}'

```

## 3.9 单位缴款统计汇总表-财政端

### 报表样式

![](report_images/image54.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 缴款日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${pay_bgndate},${pay_enddate} | fne_paybook.fpaydate |
| 2 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${fre_bgndate},${fre_enddate} | fne_paybook.freceiveddate,fpf_clear_transferfreceivedate |
| 3 | 执收单位 | 否 | 默认为空 | ${fagenidcode} | fne_paybook.fchgagenidcode |
| 4 | 收费项目 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_item.fitemidcode |
| 5 | 到账银行 | 否 | 默认为空 | ${fbankcode} | fne_unknown_capital_balance.fbankcode,fpf_clear_transfer.frecacctbankcode |
| 6 | 资金性质 | 否 | 默认为空 | ${ftype} | fne_paybook_item.ffundsnaturecode |
| 7 | 收款人帐号 | 否 | 默认为空 | ${frecacct} | fne_unknown_capital.frecacct,fpf_clear_transfer.frecacct |
| 8 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${bgndate},${enddate} | fpf_clear_transfer.FPLANDATE |

### 报表语句
``` SQL
/*宁夏：单位缴款统计汇总表*/
--研发提供  欧正鹏 20190416--
--陈国银 增加划转到账日期 20190612--
--陈国银 修改查询条件‘FPLANDATE’（划款日期）为 ‘fpaydate’（缴款日期） 20191029--
--李小文 修改 20230901 金额双倍去重--
select
'#{pay_bgndate}' as pay_bgndate,
'#{pay_enddate}' as pay_enddate,
'#{bgndate}' as hz_bgndate,
'#{enddate}' as hz_enddate,
'#{fre_bgndate}' as fre_bgndate,
'#{fre_enddate}' as fre_enddate,
total.fchgagenidcode,
total.fchgagencode,
/*decode(row_number()
over(partition by total.fchgagencode,
total.fchgagenname order by total.fchgagencode,
total.fchgagenname,
total.fitemcode,
total.fitemname),
'1',
total.fchgagenname,
'') as fchgagenname,*/
total.fchgagenname,
total.fitemidcode,
total.fitemname,
total.fitemcode,
total.fsubname,
total.fsubcode,
count(*) as ftotalnumber,
sum(total.famt) as ftotalamt,
sum(total.FISCOMPLETE) as ftransfernumber,
sum(ftransferamt) as ftransferamt,
sum(total.fisenter) as freceivednumber,
sum(freceivedamt) as freceivedamt
from (select  p.fpaycode,

p.fchgagenidcode,
p.fpaydate,
--  fp.FPLANDATE,
--  case when ub.fpaycode is not null then p.freceiveddate --else fp.freceivedate end as freceivedate, --划转到账时间
case when ub.fpaycode is not null then ub.fbankcode else fp.frecacctbankcode end as fbankcode,
p.fchgagencode,
p.fchgagenname,
pm.fitemidcode,
pm.fitemname,
pm.fitemcode,
pm.fsubname,
pm.fsubcode,
nvl(f.fimamt, pm.famt) as famt,
case when pm.famt<0 or m.fstats='9' or ub.fbalancedate is not null then '1' else m.fisenter end as fisenter,
case
when m.fisenter = '1'  or pm.famt<0 or m.fstats='9' or ub.fbalancedate is not null then
nvl(f.fimamt, pm.famt)

else
0
end as freceivedamt,
--   tf.ftransferno,
case when pm.famt<0 then '1' else fp.FISCOMPLETE end as FISCOMPLETE ,
case
when fp.FISCOMPLETE = '1'  or pm.famt<0 then
nvl(f.fimamt, pm.famt)
else
0
end as ftransferamt,
pm.FSORTNO
from fne_paybook p
left join fne_paybook_item pm
on pm.fpid = p.fid
left join fne_funddivide f
on f.fpaybooksubid = pm.fid
--and f.fclearorder = 1
left join FNE_COLLECT_TO_TRANSFER   tf on tf.FTRANSCOLLECTID  = f.fcollectid
left join fne_transfer_bank_msg m
on m.ftransno = tf.ftransferno
left join fpf_clear_transfer fp
on fp.fbatchno = tf.ftransferno
--and fp.fiscomplete = '1'
left join fne_refund_lock fr on fr.fdedpaycode=p.fpaycode and pm.famt<0
left join fpf_payrefund fp on fp.fpaycode = fr.frefpaycode
left join fne_unknown_capital_balance ub on ub.fpaycode = p.fpaycode
left join fne_unknown_capital uc on uc.fid = ub.funknownfundsid
where 1=1
and  p.fpaycode not in (select fpaycode from une_paybook_paycode)
and p.fchgagenidcode = '${fagenidcode}'
and p.fpaydate >= '${pay_bgndate}'
and p.fpaydate <= '${pay_enddate}'
and fp.FPLANDATE >= '${bgndate}'
and fp.FPLANDATE <= '${enddate}'
and (case when ub.fpaycode is not null then p.freceiveddate else fp.freceivedate end) >= '${fre_bgndate}'
and (case when ub.fpaycode is not null then p.freceiveddate else fp.freceivedate end) <= '${fre_enddate}'

and pm.fitemidcode = '${fitemidcode}'
and (case when ub.fpaycode is not null then ub.fbankcode else fp.frecacctbankcode end) = '${fbankcode}'
and (case when ub.fpaycode is not null then uc.frecacct else fp.frecacct end) = '${frecacct}'
and substr(pm.ffundsnaturecode, 1, 1) = '${ftype}'
and 1=1
) total
group by total.fchgagenidcode,
total.fchgagencode,
total.fchgagenname,
total.fitemidcode,
total.fitemname,
total.fitemcode,
total.fsubcode,
total.fsubname

```


## 3.10 单位缴款统计明细表-财政端

### 报表样式

![](report_images/image57.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 开票日期 | 否 | 包含起始日期和结束日期，默认为空 | ${bgndate},${enddate} | fne_paybook.ffilldate |
| 2 | 缴款日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${pay_bgndate},${pay_enddate} | fne_paybook.fpaydate |
| 3 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${fre_bgndate},${fre_enddate} | fne_paybook.freceiveddate,fpf_clear_transfer.freceivedate |
| 4 | 执收单位 | 否 | 默认为空 | ${fagenidcode} | fne_paybook.fchgagenidcode |
| 5 | 收费项目 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_item.fitemidcode |
| 6 | 年级 | 否 | 默认为空 | ${grade} | v_une_paybook.fcustom1 |
| 7 | 班级 | 否 | 默认为空 | ${class} | v_une_paybook.fcustom2 |
| 8 | 缴款人姓名 | 否 | 默认为空 | ${name} | v_une_paybook.fpayername，fne_paybook.fpayacctname |
| 9 | 开票人 | 否 | 默认为空 | ${fauthor} | fne_paybook.fauthor |
| 10 | 缴款渠道 | 否 | 默认为空 | ${bankcode} | fne_paybook.fpaybankcode |
| 11 | 到账银行 | 否 | 默认为空 | ${fbankcode}                  | fne_unknown_capital_balance.fbankcode,fpf_clear_transfer.frecacctbankcode |
| 12 | 资金性质 | 否 | 默认为空 | ${ftype} | fne_paybook_item.ffundsnaturecode |
| 13 | 收款人帐号 | 否 | 默认为空 | ${frecacct} | fne_unknown_capital.frecacct,fpf_clear_transfer.frecacct |
| 14 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${p_bgndate},${p_enddate} | fpf_clear_transfer.FPLANDATE |

### 报表语句
``` SQL
/*宁夏：单位缴款统计明细表*/
--研发提供  欧正鹏 201903022--
select   p.fpaycode,
d.fname,
p.fchgagencode,
p.fchgagenname,
nvl(f.fimamt, pm.famt) as famt,
case when m.fisenter = '1'  or pm.famt<0 or m.fstats='9' or ucb.fbalancedate is not null then nvl(f.fimamt, pm.famt) else 0 end as freceivedamt,
ft.FPLANDATE as fpaydate,
p.fpaydate as fpaydate2,
--u.fpayername,
case when u.fpayername is null then p.fpayacctname else u.fpayername end as fpayername,
p.fauthor,
u.fcustom1,
u.fcustom2,
u.fcustom3,
u.fcustom4,
pm.fitemname,
pm.fitemcode,
p.ffilldate,
u.fcomcbillbatchcode,
u.fbillname,
u.fcomcbillno as fbillno,
m.ftransdate,
m.ftransno,
case when ucb.fpaycode is not null then p.freceiveddate else ft.freceivedate end as fenterdate,
u.fcheckcode,
case when ucb.fpaycode is not null then uc.frecacctname else ft.frecacctname end as frecacctname,
case when ucb.fpaycode is not null then uc.frecacct else ft.frecacct end as frecacct,
case when ucb.fpaycode is not null then uc.frecacctbank else ft.frecacctopenbankname end as frecacctbank,
FSORTNO
from fne_paybook p
left join fne_paybook_item pm
on pm.fpid = p.fid
left join afa_res_dictitem d
on d.fcode = p.fpaybankcode
and d.fdictcode = '152'
left join v_une_paybook u
on u.fpaycode = p.fpaycode
left join fne_funddivide f
on f.fpaybooksubid = pm.fid
--and f.fclearorder = 1
left join fne_collect_to_transfer tf
on tf.ftranscollectid= f. fcollectid
left join fne_transfer_bank_msg m
on m.ftransno = tf.ftransferno
left join fpf_clear_transfer ft
on ft.fbatchno = tf.ftransferno and ft.fiscomplete = '1'
/*left join fne_clear_receipt cr on cr.fbatchno = tf.ftransferno
left join fne_refund_lock fr on fr.fdedpaycode=p.fpaycode and pm.famt<0
left join fpf_payrefund fp on fp.fpaycode = fr.frefpaycode  */
left join fne_unknown_capital_balance ucb on ucb.fpaycode = p.fpaycode
left join fne_unknown_capital uc on uc.fid = ucb.funknownfundsid
/*join afa_org oo
on oo.org_id = p.fchgagenidcode --and oo.org_type = 'AGEN'
join (select o.org_id, o.org_code, o.org_seq, o.org_type
from afa_org o
join afa_user u
on o.org_id = u.main_orgid
or u.user_code = 'system'
where u.user_id = '${getUser("ID")}'
-- where u.user_id='84a7342000644921930a492976c35fb1'
) tt
--on (oo.org_seq like tt.org_seq || '%' and (tt.org_type = 'AGEN' or tt.org_type = 'REGION'))
on ((oo.org_seq like tt.org_seq||'%' and (tt.org_type='AGEN' or  tt.org_type='REGION'))or tt.org_code = '640000') */
where  1=1
--((pm.famt<0 and fp.fresult='1') or pm.famt>=0)

and  p.fpaycode not in (select fpaycode from une_paybook_paycode)

and p.fchgagenidcode = '${fagenidcode}'
and p.fpaybankcode = '${bankcode}'
and ft.FPLANDATE >= '${p_bgndate}'
and ft.FPLANDATE <= '${p_enddate}'
and p.fpaydate>= '${pay_bgndate}'
and p.fpaydate<= '${pay_enddate}'
and p.fpaydate = '${fpaydate}'
and p.ffilldate >= '${bgndate}'
and p.ffilldate <= '${enddate}'
and (case when ucb.fpaycode is not null then p.freceiveddate else ft.freceivedate end) >= '${fre_bgndate}'
and (case when ucb.fpaycode is not null then p.freceiveddate else ft.freceivedate end) <= '${fre_enddate}'
-- and decode(m.fstats,'9',nvl(m.fenterdate,cr.fdate),m.fenterdate)   >= '${fre_bgndate}'
-- and decode(m.fstats,'9',nvl(m.fenterdate,cr.fdate),m.fenterdate)   <= '${fre_enddate}'
and pm.fitemidcode = '${fitemidcode}'
and u.fcustom2 like '${class}%'
and u.fcustom1 like '${grade}%'
and (u.fpayername like '${name}%' or p.fpayacctname like '${name}%')
and p.fauthor like '${fauthor}'
and (case when ucb.fpaycode is not null then ucb.fbankcode else ft.frecacctbankcode end) = '${fbankcode}'
and (case when ucb.fpaycode is not null then uc.frecacct else ft.frecacct end) = '${frecacct}'
and substr(pm.ffundsnaturecode, 1, 1) = '${ftype}'
order by p.fchgagencode, p.fpaycode, pm.fitemcode

```

## 3.11 单位缴款统计汇总表（项目）-财政端

### 报表样式

![](report_images/image60.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 缴款日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${pay_bgndate},${pay_enddate} | fne_paybook.fpaydate |
| 2 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${bgndate},${enddate} | fpf_clear_transfer.FPLANDATE |
| 3 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${fre_bgndate},${fre_enddate} | fne_unknown_capital_balance.fbalancedate,fpf_clear_transfer.freceivedate |
| 4 | 执收单位 | 否 | 默认为空 | ${fagenidcode} | fne_paybook.fchgagenidcode |
| 5 | 收费项目 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_item.fitemidcode |
| 6 | 到账银行 | 否 | 默认为空 | ${fbankcode} | fne_unknown_capital_balance.fbankcode,fpf_clear_transfer.frecacctbankcode |
| 7 | 资金性质 | 否 | 默认为空 | ${ftype} | fne_paybook_item.ffundsnaturecode |

### 报表语句
``` SQL
/*宁夏：单位缴款统计汇总表*/
--研发提供  欧正鹏 20190416--
--陈国银 增加划转到账日期 20190612--
--陈国银 修改查询条件‘FPLANDATE’（划款日期）为 ‘fpaydate’（缴款日期） 20191029--
select
'#{pay_bgndate}' as pay_bgndate,
'#{pay_enddate}' as pay_enddate,
'#{bgndate}' as hz_bgndate,
'#{enddate}' as hz_enddate,
'#{fre_bgndate}' as fre_bgndate,
'#{fre_enddate}' as fre_enddate,
total.fchgagenidcode,
total.fchgagencode,
decode(row_number()
over(partition by total.fchgagencode,
total.fchgagenname order by total.fchgagencode,
total.fchgagenname,
total.fitemcode,
total.fitemname),
'1',
total.fchgagenname,
'') as fchgagenname,
total.fitemidcode,
total.fitemname,
total.fitemcode,
total.fsubname,
total.fsubcode,
count(*) as ftotalnumber,
sum(total.famt) as ftotalamt,
sum(total.FISCOMPLETE) as ftransfernumber,
sum(ftransferamt) as ftransferamt,
sum(total.fisenter) as freceivednumber,
sum(freceivedamt) as freceivedamt
from (select distinct p.fpaycode,

p.fchgagenidcode,
p.fpaydate,
fp.FPLANDATE,
case when ub.fpaycode is not null then ub.fbalancedate else fp.freceivedate end as freceivedate, --划转到账时间
case when ub.fpaycode is not null then ub.fbankcode else fp.frecacctbankcode end as fbankcode,
p.fchgagencode,
p.fchgagenname,
pm.fitemidcode,
pm.fitemname,
pm.fitemcode,
pm.fsubname,
pm.fsubcode,
pm.famt,
case when pm.famt<0 or m.fstats='9' or ub.fbalancedate is not null then '1' else m.fisenter end as fisenter,
case
when m.fisenter = '1'  or pm.famt<0 or m.fstats='9' or ub.fbalancedate is not null then
pm.famt

else
0
end as freceivedamt,
tf.ftransferno,
case when pm.famt<0 then '1' else fp.FISCOMPLETE end as FISCOMPLETE ,
case
when fp.FISCOMPLETE = '1'  or pm.famt<0 then
pm.famt
else
0
end as ftransferamt,
pm.FSORTNO
from fne_paybook p
left join fne_paybook_item pm
on pm.fpid = p.fid
left join fne_funddivide f
on f.fpaybooksubid = pm.fid
and f.fclearorder = 1
left join FNE_COLLECT_TO_TRANSFER   tf on tf.FTRANSCOLLECTID  = f.fcollectid
left join fne_transfer_bank_msg m
on m.ftransno = tf.ftransferno
left join fpf_clear_transfer fp
on fp.fbatchno = tf.ftransferno
and fp.fiscomplete = '1'
left join fne_refund_lock fr on fr.fdedpaycode=p.fpaycode and pm.famt<0
left join fpf_payrefund fp on fp.fpaycode = fr.frefpaycode
left join fne_unknown_capital_balance ub on ub.fpaycode = p.fpaycode
/*left join fab_subject s
--on s.fsubcode = f.fsubcode
on pm.fsubid = s.fid
and s.fyear = substr(fp.FPLANDATE, 0, 4) --缴款书日期的年份 */

where 1=1
--((pm.famt<0 and fp.fresult='1') or pm.famt>=0)
and p.fchgagenidcode = '${fagenidcode}'
and p.fpaydate >= '${pay_bgndate}'
and p.fpaydate <= '${pay_enddate}'
and fp.FPLANDATE >= '${bgndate}'
and fp.FPLANDATE <= '${enddate}'
and (case when ub.fpaycode is not null then ub.fbalancedate else fp.freceivedate end) >= '${fre_bgndate}'
and (case when ub.fpaycode is not null then ub.fbalancedate else fp.freceivedate end) <= '${fre_enddate}'
and pm.fitemidcode = '${fitemidcode}'
and (case when ub.fpaycode is not null then ub.fbankcode else fp.frecacctbankcode end) = '${fbankcode}'
and substr(pm.ffundsnaturecode, 1, 1) = '${ftype}'
and 1=1
) total
group by total.fchgagenidcode,
total.fchgagencode,
total.fchgagenname,
total.fitemidcode,
total.fitemname,
total.fitemcode,
total.fsubcode,
total.fsubname

```


## 3.12 财政库存票据汇总查询-财政端

### 报表样式

![](report_images/image62.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 日期 | 否 | 包含起始日期和结束日期，默认为空 | ${date_bgn},${date_end} | fbe_stock_in.fdate |
| 2 | 票据 | 否 | 默认为空 | ${fbillid} | fbe_stock_in_item.fbillid |
| 3 | 印刷企业 | 否 | 默认为空 | ${fcompanyid} | fbe_stock_in.fcompanyid |

### 报表语句
``` SQL
with t1 as(   --本期期初库存
select
a.fbillid,
b.fbillcode,
b.fbillname,
b.funits,
a.fbatchcode,
sum(a.fnumber) fnumber
from
(select  --期初库存
ii.fbillid,
decode(ii.fbatchcode,'010618','010618BA',ii.fbatchcode) fbatchcode,
sum(ii.fnumber) fnumber
from fbe_stock_initial i
join fbe_stock_initial_item ii
on i.fid = ii.fpid
where i.frgncode = '640000'
and ii.fbillid = '${fbillid}'
group by ii.fbillid,decode(ii.fbatchcode,'010618','010618BA',ii.fbatchcode)
union all
select  --入库
ii.fbillid,
ii.fbatchcode,
sum(ii.fnumber) fnumber
from fbe_stock_in i
join fbe_stock_in_item ii
on i.fid = ii.fpid
where i.frgncode = '640000'
and ii.fbillid = '${fbillid}'
and i.fcompanyid = '${fcompanyid}'
and i.fdate < '${date_bgn}'
group by ii.fbillid,ii.fbatchcode
union all
select  --出库
ii.fbillid,
ii.fbatchcode,
sum(-ii.fnumber) fnumber
from fbe_stock_out i
join fbe_stock_out_item ii
on i.fid = ii.fpid
where i.frgncode = '640000'
and ii.fbillid = '${fbillid}'
and i.fdate < '${date_bgn}'
group by ii.fbillid,ii.fbatchcode
union all
select  --申退
ii.fbillid,
ii.fbatchcode,
sum(ii.fnumber) fnumber
from fbe_stock_receivereturn i
join fbe_stock_receivereturn_item ii
on i.fid = ii.fpid
where i.frgncode = '640000'
and ii.fbillid = '${fbillid}'
and i.freturndate < '${date_bgn}'
group by ii.fbillid,ii.fbatchcode) a
left join fab_bill b
on b.fid=a.fbillid
where b.fissort = '0'
and b.fexpdate >= to_char(sysdate,'yyyy-mm-dd')
group by a.fbillid,a.fbatchcode,b.fbillcode,b.fbillname,funits
) ,

t2 as (  --本期入库
select
ii.fbillid,
ii.fbatchcode,
i.fdate,
p.fname fcompanyname,
ii.fprice,
ii.famt,
ii.fbillno1,
ii.fbillno2,
ii.fnumber
from fbe_stock_in i
join fbe_stock_in_item ii
on i.fid = ii.fpid
left join fbb_prtcompany p
on i.fcompanyid = p.fid
where i.frgncode = '640000'
and ii.fbillid = '${fbillid}'
and i.fcompanyid = '${fcompanyid}'
and i.fdate >= '${date_bgn}'
and i.fdate <= '${date_end}'
and 1=1
),

t3 as (  --本期出库
select
fbillid,
fbatchcode,
min(fbillno1) fbillno1,
max(fbillno2) fbillno2,
sum(fnumber) fnumber
from(
select
ii.fbillid,
ii.fbatchcode,
min(ii.fbillno1) fbillno1,
max(ii.fbillno2) fbillno2,
sum(ii.fnumber) fnumber
from fbe_stock_out i
join fbe_stock_out_item ii
on i.fid = ii.fpid
where i.frgncode = '640000'
and ii.fbillid = '${fbillid}'
and i.fdate >= '${date_bgn}'
and i.fdate <= '${date_end}'
group by ii.fbillid,ii.fbatchcode
union all
select  --申退
ii.fbillid,
ii.fbatchcode,
min(ii.fbillno1) fbillno1,
max(ii.fbillno2) fbillno2,
sum(-ii.fnumber) fnumber
from fbe_stock_receivereturn i
join fbe_stock_receivereturn_item ii
on i.fid = ii.fpid
where i.frgncode = '640000'
and ii.fbillid = '${fbillid}'
and i.freturndate >= '${date_bgn}'
and i.freturndate <= '${date_end}'
group by ii.fbillid,ii.fbatchcode)
group by fbillid,fbatchcode
),

t4 as (  --入库汇总
select
ii.fbillid,
ii.fbatchcode,
sum(ii.fnumber) fnumber
from fbe_stock_in i
join fbe_stock_in_item ii
on i.fid = ii.fpid
left join fbb_prtcompany p
on i.fcompanyid = p.fid
where i.frgncode = '640000'
and ii.fbillid = '${fbillid}'
and i.fcompanyid = '${fcompanyid}'
and i.fdate >= '${date_bgn}'
and i.fdate <= '${date_end}'
group by ii.fbillid,ii.fbatchcode
)

select
decode(row_number() over(partition by t1.fbillcode,t1.fbatchcode order by t2.fdate),1,t1.fbillcode,'') fbillcode,
decode(row_number() over(partition by t1.fbillcode,t1.fbatchcode order by t2.fdate),1,t1.fbillname,'') fbillname,
decode(row_number() over(partition by t1.fbillcode,t1.fbatchcode order by t2.fdate),1,t1.fbatchcode,'') fbatchcode,
decode(row_number() over(partition by t1.fbillcode,t1.fbatchcode order by t2.fdate),1,t1.fnumber,'') qckc,
t2.fnumber rksl,
t2.fdate rkdate,
t2.fcompanyname,
t2.fprice,
t2.famt,
(select fname from afa_res_dictitem where fdictcode='126' and fcode=t1.funits) as jldw,
t2.fbillno1 rkno1,
t2.fbillno2 rkno2,
decode(row_number() over(partition by t1.fbillcode,t1.fbatchcode order by t2.fdate),1,t3.fnumber,'') cksl,
decode(row_number() over(partition by t1.fbillcode,t1.fbatchcode order by t2.fdate),1,t3.fbillno1,'') ckno1,
decode(row_number() over(partition by t1.fbillcode,t1.fbatchcode order by t2.fdate),1,t3.fbillno2,'') ckno2,
decode(row_number() over(partition by t1.fbillcode,t1.fbatchcode order by t2.fdate),1,
nvl(t1.fnumber,0)+nvl(t4.fnumber,0)-nvl(t3.fnumber,0),'') jykc
from t2
left join t1
on t2.fbillid=t1.fbillid
and t2.fbatchcode=t1.fbatchcode
left join t3
on t2.fbillid=t3.fbillid
and t2.fbatchcode=t3.fbatchcode
left join t4
on t2.fbillid=t4.fbillid
and t2.fbatchcode=t4.fbatchcode
order by t1.fbillcode,t1.fbatchcode,t2.fdate

```

## 3.13 单位资金划转对账表-财政端

### 报表样式

![](report_images/image64.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收单位 | 否 | 默认为空 | ${fchgagenidcode} | fne_paybook.fchgagenidcode |
| 2 | 缴款日期 | 否 | 包含起始日期和结束日期，默认为空 | ${pay_bgndate},${pay_enddate} | fne_paybook.fpaydate |
| 3 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${trans_bgndate},${trans_enddate} | fpf_clear_transfer.FPLANDATE |
| 4 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${enter_bgndate},${enter_enddate} | fpf_clear_transfer.freceivedate |
| 5 | 收款账户类型 | 否 | 默认为空 | ${frecaccttype} | fne_capital_transfer.frecaccttype |
| 6 | 结算渠道 | 否 | 默认为空 | ${fbankcode} | fne_capital_transfer.fbankcode |
| 7 | 结算批次号 | 否 | 默认为空 | ${ftransno} | fne_capital_transfer.ftransno |
| 8 | 到账银行 | 否 | 默认为空 | ${frecbankcode} | fne_capital_transfer.frecbankcode |
| 9 | 收款账号 | 否 | 默认为空 | ${frecacct} | fne_capital_transfer.frecacct |

### 报表语句
``` SQL
/*宁夏：单位资金划转对账表（财政端）*/
----研发提供  欧正鹏 20190401----
select t.ftransno,
'ZX'||substr(t.ftransno,4,6)||N10_TO_62(substr(t.ftransno,10,6)||
f_16_tr_10(substr(t.ftransno,16,7))) as fmemo,
t.frecacctname,
t.frecacct,
case  t.frecaccttype
when '0' then
'虚拟账户'
when '1' then
'财政专户'
when '2' then
'汇缴专户'
when '3' then
'待解缴科目'
when '4' then
'单位监管账户'
when '5' then
'国库账户'
when '7' then
'单位清分账户'
else
'其他'
end as frecaccttype,
dict.fname as frecbankname,
sum(nvl(f.fimamt, pm.famt))as famt,
b.fname,
p.fpaymentchannel,
fp.FPLANDATE as ftransferdate,
fp.freceivedate as fenterdate,
t.fbankcode
from fne_paybook p
left join fne_paybook_item pm
on pm.fpid = p.fid
left join fne_funddivide f
on pm.fid = f.fpaybooksubid
--on f.fpaycode = p.fpaycode
--and f.fitemcode = pm.fitemcode
left join FNE_COLLECT_TO_TRANSFER   tf on tf.FTRANSCOLLECTID  = f.fcollectid
join fne_capital_transfer t
on t.ftransno = tf.ftransferno
join afa_res_dictitem dict
on dict.fcode = t.frecbankcode
and dict.fdictcode = '152'
left join fpf_clear_transfer fp
on fp.fbatchno = tf.ftransferno and fp.fiscomplete = '1'
left join fpf_bank b
on b.fcode = t.fbankcode
join afa_org oo
on oo.org_id = p.fchgagenidcode--and oo.org_type = 'AGEN'
join (select o.org_id, o.org_code, o.org_seq, o.org_type
from afa_org o
join afa_user u
on o.org_id = u.main_orgid
or u.user_code = 'system'
where u.user_id = '${getUser("ID")}'
-- where u.user_id='913fcadd614d42758f897becafa06c4a'
) tt
on ((oo.org_seq like tt.org_seq||'%' and (tt.org_type='AGEN' or  tt.org_type='REGION'))or tt.org_code = '640000')
where fp.FPLANDATE >= '${trans_bgndate}'
and fp.FPLANDATE <= '${trans_enddate}'
and fp.freceivedate >= '${enter_bgndate}'
and fp.freceivedate <= '${enter_enddate}'
and p.fpaydate >= '${pay_bgndate}'
and p.fpaydate <= '${pay_enddate}'
and t.fbankcode = '${fbankcode}'
and t.frecaccttype = '${frecaccttype}'
and t.frecacct = '${frecacct}'
and t.ftransno like '${ftransno}%'
and p.fchgagenidcode = '${fchgagenidcode}'
and t.frecbankcode = '${frecbankcode}'
group by t.ftransno,
t.frecacctname,
t.frecacct,
t.frecaccttype,
dict.fname,
b.fname,
p.fpaymentchannel,
fp.FPLANDATE,
fp.freceivedate,
t.fbankcode
order by fp.FPLANDATE, t.fbankcode

```

## 3.14 单位资金划转对账明细表-财政端

### 报表样式

![](report_images/image66.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收单位 | 否 | 默认为空 | ${fchgagenidcode} | fne_paybook.fchgagenidcode |
| 2 | 项目名称 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_item.fitemidcode |
| 3 | 缴款日期 | 否 | 包含起始日期和结束日期，默认为空 | ${pay_bgndate},${pay_enddate} | fne_paybook.fpaydate |
| 4 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${trans_bgndate},${trans_enddate} | fpf_clear_transfer.FPLANDATE |
| 5 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${enter_bgndate},${enter_enddate} | fpf_clear_transfer.freceivedate |
| 6 | 结算渠道 | 否 | 默认为空 | ${fbankcode} | fne_capital_transfer.fbankcode |
| 7 | 收款账户类型 | 否 | 默认为空 | ${frecaccttype} | fne_capital_transfer.frecaccttype |
| 8 | 结算批次号 | 否 | 默认为空 | ${ftransno} | fne_capital_transfer.ftransno |
| 9 | 缴款人名称 | 否 | 默认为空 | ${fpayername} | v_une_paybook.fpayername |
| 10 | 收款银行名称 | 否 | 默认为空 | ${frecacctname} | fne_paybook.frecacctname |
| 11 | 电子缴款码 | 否 | 默认为空 | ${fpaycode} | fne_paybook.fpaycode |

### 报表语句
``` SQL
/*宁夏：单位资金划转对账明细表(财政)*/
----研发提供  欧正鹏 20190322----
/*修改：陈国银 20190328*/
select
p.fpaycode,
p.fchgagencode,
p.fchgagenidcode,
p.fchgagenname,
u.fbillname,
u.fcomcbillno as fbillno,
u.fpayername,
u.fcustom1,
u.fcustom2,
u.fcustom3,
u.fcustom4,
t.frecacctname,
t.frecacct,
f.fitemcode,
f.fitemname,
--pm.fitemcode,
--pm.fitemname,
--pm.famt,
nvl(f.fimamt, pm.famt) as famt,
fp.FPLANDATE as ftransdate,
fp.freceivedate as fenterdate,
t.ftransno
from fne_paybook p
left join fne_paybook_item pm
on pm.fpid = p.fid
left join v_une_paybook u
on u.fpaycode = p.fpaycode
left join fne_funddivide f
on pm.fid = f.fpaybooksubid
and f.fpaycode = p.fpaycode
left join FNE_COLLECT_TO_TRANSFER   tf on tf.FTRANSCOLLECTID  = f.fcollectid
left join fne_capital_transfer t
on t.ftransno = tf.ftransferno
left join fpf_clear_transfer fp
on fp.fbatchno = tf.ftransferno and fp.fiscomplete = '1'
join afa_org oo
on oo.org_id = p.fchgagenidcode  --and oo.org_type = 'AGEN'
join (select o.org_id, o.org_code, o.org_seq, o.org_type
from afa_org o
join afa_user u
on o.org_id = u.main_orgid
or u.user_code = 'system'
where u.user_id = '${getUser("ID")}'
--where u.user_id='913fcadd614d42758f897becafa06c4a'
) tt
on ((oo.org_seq like tt.org_seq||'%' and (tt.org_type='AGEN' or  tt.org_type='REGION'))or tt.org_code = '640000')
where fp.FPLANDATE >= '${trans_bgndate}'
and fp.FPLANDATE <= '${trans_enddate}'
and fp.freceivedate >= '${enter_bgndate}'
and fp.freceivedate <= '${enter_enddate}'
and p.fpaydate >= '${pay_bgndate}'
and p.fpaydate <= '${pay_enddate}'
and t.fbankcode = '${fbankcode}'
and t.frecaccttype = '${frecaccttype}'
and t.ftransno like '${ftransno}%'
and p.fchgagenidcode = '${fchgagenidcode}'
and u.fpayername like '${fpayername}%'
and p.frecacctname like '${frecacctname}'
and p.fpaycode like '${fpaycode}$'
and pm.fitemidcode = '${fitemidcode}'
order by fp.FPLANDATE,t.fbankcode,p.fpaycode

```

## 3.15 分批缴款汇总统计报表-财政端

### 报表样式

![](report_images/image68.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 缴款日期 | 否 | 包含起始日期和结束日期，默认为空 | ${date_bgn},${date_end} | une_paybook.fdate |
| 2 | 执收单位 | 否 | 默认为空 | ${agen} | une_paybook.faccagenidcode |
| 3 | 收费项目 | 否 | 默认为空 | ${item} | une_paybook_item.fitemidcode |
| 4 | 缴款码 | 否 | 默认为空 | ${paycode} | une_paybook.fpaycode |
| 5 | 年级 | 否 | 默认为空 | ${grade} | une_paybook.fcustom1 |
| 6 | 班级 | 否 | 默认为空 | ${class} | une_paybook.fcustom2 |
| 7 | 姓名 | 否 | 默认为空 | ${xinming} | une_paybook.fpayername |
| 8 | 身份证号 | 否 | 默认为空 | ${sfzno} | une_paybook.fcustom3 |
| 9 | 学籍号 | 否 | 默认为空 | ${xuejino} | une_paybook.fcustom4 |
| 10 | 缴款状态 | 否 | 默认为空 | ${state} | une_paybook.fstate |
| 11 | 是否换开纸质票 | 否 | 默认为空 | ${hstate} | une_paybook.fstate |
| 12 | 是否已缴全 | 否 | 默认为空 | ${jiaoquan} | 函数公式计算：une_paybook.fcustom5减去une_paybook.ftotalamt |
| 13 | 是否显示明细 | 是 | 默认为1 | ${mingxi} | 前端选择0或1 |

### 报表语句
``` SQL
with t as
(
select row_number() over(partition by fcustom6 order by fcustom6 ,fupdatetime) as paixu,
fpaycode, --缴款码
fplacename, --开票点名称
fauthor, --开票人
fdate, --开票日期
fbillno, --电子票号
frelatedno, --相关纸质票号
state, --缴款状态
hstate,--换开状态
fconfirmdate, --缴款日期
fpayername, --付款人全称
fpayerno, --付款人账号
fcustom1, --年级
fcustom2, --班级
fcustom3, --身份证号
fcustom4, --学籍号
famt， ----本次缴款金额
yinjiaoamt， --应缴金额
shijiaoamt, --实缴金额
--daijiaoamt, --待缴金额
fitemcode, --收费项目编码
fitemname, -- 收费项目名称
fcustom6, --缴款批次号
fupdatetime
--mingxi
from (
--展示明细，已缴款
select --1 as mingxi,
t.fpaycode, --缴款码
t.fplacename, --开票点名称
t.fauthor, --开票人
--t.fdate, --开票日期
to_char(to_date((substr(t.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss') fdate,--开票日期
t.fbillno, --电子票号
-- decode(c.fbustype, 2, c.frelatedbillno, '') frelatedno, --相关纸质票号
t. fcompBillNo frelatedno, --相关纸质票号
decode(t.fstate,1,'未缴款',2,'作废',3,'已缴款确认',4,'电子转纸质票据', '', '未缴款') state, --缴款状态
case when   t.fcompbillno is not NULL then '已开纸质票据'
when t.fcompbillno is NULL  then '未开纸质票据'
end  hstate,--换开状态
--t.fconfirmdate, --缴款日期
to_char(to_date((substr(uc.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss')fconfirmdate,--缴款日期
t.fpayername, --付款人全称
t.fpayerno, --付款人账号
t.fcustom1, --年级
t.fcustom2, --班级
t.fcustom3, --身份证号
t.fcustom4, --学籍号
to_char(ti.famt)famt， ----本次缴款金额
to_char(t.fcustom5) yinjiaoamt， --应缴金额
to_char(t.ftotalamt) shijiaoamt, --实缴金额
--(t.fcustom5 - t.ftotalamt) daijiaoamt, --待缴金额

ti.fitemcode, --收费项目编码
ti.fitemname, -- 收费项目名称

t.fcustom6, --缴款批次号
t.fupdatetime
from une_paybook t
left join une_paybook_item ti
on t.fid = ti.fpid
left join une_paybook_confirm uc
on uc.fpaycode = t.fpaycode
--left join une_cbill c  on c.fpaycode = t.fpaycode
/*join uab_place_user p on t.fplaceid  = p.fplaceid
and p.fuserid = '${getUser("ID")}' */
where t.fstate = '3'

and t.fdate>='${date_bgn}' and t.fdate<='${date_end}'
and t.fpaycode like '${paycode}%'
and t.faccagenidcode='${agen}'
and t.fcustom1='${grade}'
and t.fcustom2='${class}'
and nvl(t.fstate,1)='${state}'
and ti.fitemidcode='${item}'
and t.fpayername like '%${xinming}%'
and t.fcustom3 like '${sfzno}%'
and t.fcustom4 like '${xuejino}%'
and 1=1

union all
--展示明细，未缴款
select --1 as mingxi,
t.fpaycode, --缴款码
t.fplacename, --开票点名称
t.fauthor, --开票人
--t.fdate, --开票日期
to_char(to_date((substr(t.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss') fdate,--开票日期
'' as fbillno, --电子票号
'' frelatedno, --相关纸质票号

decode(t.fstate,1,'未缴款',2,'作废',3,'已缴款确认',4,'电子转纸质票据', '', '未缴款') state, --缴款状态
'未开纸质票据'hstate,
--t.fconfirmdate, --缴款日期
to_char(to_date((substr(uc.fcreatetime,0,14)), 'yyyymmddhh24miss'), 'yyyy-mm-dd hh24:mi:ss')fconfirmdate,--缴款日期
t.fpayername, --付款人全称
t.fpayerno, --付款人账号
t.fcustom1, --年级
t.fcustom2, --班级
t.fcustom3, --身份证号
t.fcustom4, --学籍号
to_char('0') famt， ----本次缴款金额
to_char(t.fcustom5) yinjiaoamt， --应缴金额
to_char('0') shijiaoamt, --实缴金额
--(t.fcustom5 - 0) daijiaoamt, --待缴金额
ti.fitemcode, --收费项目编码
ti.fitemname, -- 收费项目名称
t.fcustom6, --缴款批次号
t.fupdatetime
from une_paybook t
left join une_paybook_item ti
on t.fid = ti.fpid
left join une_paybook_confirm uc
on uc.fpaycode = t.fpaycode
/*join uab_place_user p on t.fplaceid  = p.fplaceid
and p.fuserid = '${getUser("ID")}' */
where t.fstate <> '3'
and t.fdate>='${date_bgn}' and t.fdate<='${date_end}'
and t.fpaycode like '${paycode}%'
and t.faccagenidcode='${agen}'
and t.fcustom1='${grade}'
and t.fcustom2='${class}'
and nvl(t.fstate,1)='${state}'
and ti.fitemidcode='${item}'
and t.fpayername like '%${xinming}%'
and t.fcustom3 like '${sfzno}%'
and t.fcustom4 like '${xuejino}%'
and 1=1
)where hstate = '${hstate}'
and 1=1
)
select
fpaycode,--缴款码
fplacename,--开票点名称
fauthor,--开票人
fdate,--开票日期
fbillno,--电子票号
frelatedno,--相关纸质票号
state,--缴款状态
hstate,--换开状态
fconfirmdate,--缴款日期
fpayername,--付款人全称
fpayerno,--付款人账号
fcustom1,--年级
fcustom2,--班级
fcustom3,--身份证号
fcustom4,--学籍号
famt，----本次缴款金额
yinjiaoamt， --应缴金额
shijiaoamt,--实缴金额
daijiaoamt, --待缴金额
fitemcode,--收费项目编码
fitemname,  -- 收费项目名称
fcustom6, --缴款批次号
mingxi,
jiaoquan,
fupdatetime
from
(
select
--paixu,
fpaycode, --缴款码
fplacename, --开票点名称
fauthor, --开票人
fdate, --开票日期
fbillno, --电子票号
frelatedno, --相关纸质票号
state, --缴款状态
hstate,--换开状态
fconfirmdate, --缴款日期
fpayername, --付款人全称
fpayerno, --付款人账号
fcustom1, --年级
fcustom2, --班级
fcustom3, --身份证号
fcustom4, --学籍号
famt， ----本次缴款金额
yinjiaoamt， --应缴金额
shijiaoamt, --实缴金额
(yinjiaoamt-shijiaoamt) daijiaoamt, --待缴金额
fitemcode, --收费项目编码
fitemname, -- 收费项目名称
fcustom6, --缴款批次号
'1'mingxi,
case when (yinjiaoamt-shijiaoamt) =0 then '1'
else '0' end jiaoquan,
fupdatetime
from
(
select --paixu,
fpaycode, --缴款码
fplacename, --开票点名称
fauthor, --开票人
fdate, --开票日期
fbillno, --电子票号
frelatedno, --相关纸质票号
state, --缴款状态
hstate,--换开状态
fconfirmdate, --缴款日期
fpayername, --付款人全称
fpayerno, --付款人账号
fcustom1, --年级
fcustom2, --班级
fcustom3, --身份证号
fcustom4, --学籍号
famt， ----本次缴款金额
to_char(decode (paixu ,'1',yinjiaoamt,'2',(lag((yinjiaoamt-shijiaoamt),1,0) over(order by fcustom6 nulls first,fupdatetime)),'0'))yinjiaoamt,--应缴金额
shijiaoamt, --实缴金额
fitemcode, --收费项目编码
fitemname, -- 收费项目名称
fcustom6, --缴款批次号
fupdatetime
--mingxi
from t
order by fcustom6,yinjiaoamt

)
union all
select
--paixu,
'' fpaycode,--缴款码
'' fplacename,--开票点名称
'' fauthor,--开票人
'' fdate,--开票日期
''  fbillno,--电子票号
'' frelatedno,--相关纸质票号
state,--缴款状态
hstate,--换开状态
''  fconfirmdate,--缴款日期
fpayername,--付款人全称
fpayerno,--付款人账号
fcustom1,--年级
fcustom2,--班级
fcustom3,--身份证号
fcustom4,--学籍号
to_char(sum (famt)) famt，----本次缴款金额
to_char (sum (yinjiaoamt)) yinjiaoamt， --应缴金额
to_char (sum (shijiaoamt)) shijiaoamt,--实缴金额
sum (yinjiaoamt-shijiaoamt) daijiaoamt, --待缴金额

''fitemcode,--收费项目编码
''fitemname,  -- 收费项目名称

fcustom6, --缴款批次号
'0'mingxi,
--decode (sum (fcustom5-ftotalamt),0,'已缴全'，'未缴全') jiaoquan
case when sum (yinjiaoamt-shijiaoamt) =0 then '1'
else '0' end jiaoquan,
fupdatetime
from
(   select
--paixu,
fpaycode, --缴款码
fplacename, --开票点名称
fauthor, --开票人
fdate, --开票日期
fbillno, --电子票号
frelatedno, --相关纸质票号
state, --缴款状态
hstate,--换开状态
fconfirmdate, --缴款日期
fpayername, --付款人全称
fpayerno, --付款人账号
fcustom1, --年级
fcustom2, --班级
fcustom3, --身份证号
fcustom4, --学籍号
famt， ----本次缴款金额
yinjiaoamt， --应缴金额
shijiaoamt, --实缴金额
(yinjiaoamt-shijiaoamt) daijiaoamt, --待缴金额
fitemcode, --收费项目编码
fitemname, -- 收费项目名称
fcustom6, --缴款批次号
fupdatetime
from
(
select --paixu,
fpaycode, --缴款码
fplacename, --开票点名称
fauthor, --开票人
fdate, --开票日期
fbillno, --电子票号
frelatedno, --相关纸质票号
state, --缴款状态
hstate,--换开状态
fconfirmdate, --缴款日期
fpayername, --付款人全称
fpayerno, --付款人账号
fcustom1, --年级
fcustom2, --班级
fcustom3, --身份证号
fcustom4, --学籍号
famt， ----本次缴款金额
to_char(decode (paixu ,'1',yinjiaoamt,'2',(lag((yinjiaoamt-shijiaoamt),1,0) over(order by fcustom6,fupdatetime)),'0'))yinjiaoamt,--应缴金额
shijiaoamt, --实缴金额
fitemcode, --收费项目编码
fitemname, -- 收费项目名称
fcustom6, --缴款批次号
fupdatetime
from t)
)
group by fcustom6,
(
state，
hstate,--换开状态
fpayername,
fpayerno,
fcustom1,
fcustom2,
fcustom3,
fcustom4,
fupdatetime)
order by fcustom6,yinjiaoamt
)
where mingxi='${mingxi}'
and jiaoquan = '${jiaoquan}'

```

## 3.16 单位端单位缴款统计汇总表-单位端

### 报表样式

![](report_images/image70.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 缴款日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${pay_bgndate},${pay_enddate} | fne_paybook.fpaydate |
| 2 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${fre_bgndate},${fre_enddate} | fne_paybook.freceiveddate,fpf_clear_transfer.freceivedate |
| 3 | 执收单位 | 否 | 默认为空 | ${fchgagenidcode} | fne_paybook.fchgagenidcode |
| 4 | 收费项目 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_item.fitemidcode |
| 5 | 到账银行 | 否 | 默认为空 | ${fbankcode} | fne_unknown_capital_balance.fbankcode,fpf_clear_transfer.frecacctbankcode |
| 6 | 资金性质 | 否 | 默认为空 | ${ftype} | fne_paybook_item.ffundsnaturecode |
| 7 | 收款人帐号 | 否 | 默认为空 | ${frecacct} | fne_unknown_capital.frecacct,fpf_clear_transfer.frecacct |
| 8 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${bgndate},${enddate} | fpf_clear_transfer.FPLANDATE |

### 报表语句
``` SQL
/*宁夏：单位缴款统计汇总表*/
select
'#{pay_bgndate}' as pay_bgndate,
'#{pay_enddate}' as pay_enddate,
'#{bgndate}' as hz_bgndate,
'#{enddate}' as hz_enddate,
'#{fre_bgndate}' as fre_bgndate,
'#{fre_enddate}' as fre_enddate,
total.fchgagenidcode,
total.fchgagencode,
/*decode(row_number()
over(partition by total.fchgagencode,
total.fchgagenname order by total.fchgagencode,
total.fchgagenname,
total.fitemcode,
total.fitemname),
'1',
total.fchgagenname,
'') as fchgagenname,*/
total.fchgagenname,
total.fitemidcode,
total.fitemname,
total.fitemcode,
total.fsubname,
total.fsubcode,
count(*) as ftotalnumber,
sum(total.famt) as ftotalamt,
sum(total.FISCOMPLETE) as ftransfernumber,
sum(ftransferamt) as ftransferamt,
sum(total.fisenter) as freceivednumber,
sum(freceivedamt) as freceivedamt
from (select  p.fpaycode,
p.fchgagenidcode,
p.fpaydate,
--  fp.FPLANDATE,
--  case when ub.fpaycode is not null then p.freceiveddate --else fp.freceivedate end as freceivedate, --划转到账时间
case when ub.fpaycode is not null then ub.fbankcode else fp.frecacctbankcode end as fbankcode,
p.fchgagencode,
p.fchgagenname,
pm.fitemidcode,
pm.fitemname,
pm.fitemcode,
pm.fsubname,
pm.fsubcode,
nvl(f.fimamt, pm.famt) as famt,
case when pm.famt<0 or m.fstats='9' or ub.fbalancedate is not null then '1' else m.fisenter end as fisenter,
case
when m.fisenter = '1'  or pm.famt<0 or m.fstats='9' or ub.fbalancedate is not null then
nvl(f.fimamt, pm.famt)

else
0
end as freceivedamt,
--   tf.ftransferno,
case when pm.famt<0 then '1' else fp.FISCOMPLETE end as FISCOMPLETE ,
case
when fp.FISCOMPLETE = '1'  or pm.famt<0 then
nvl(f.fimamt, pm.famt)
else
0
end as ftransferamt,
pm.FSORTNO
from fne_paybook p
left join fne_paybook_item pm
on pm.fpid = p.fid
left join une_paybook up
on p.fpaycode = up.fpaycode
left join fne_funddivide f
on f.fpaybooksubid = pm.fid
--and f.fclearorder = 1
left join FNE_COLLECT_TO_TRANSFER   tf on tf.FTRANSCOLLECTID  = f.fcollectid
left join fne_transfer_bank_msg m
on m.ftransno = tf.ftransferno
left join fpf_clear_transfer fp
on fp.fbatchno = tf.ftransferno
--and fp.fiscomplete = '1'
left join fne_refund_lock fr on fr.fdedpaycode=p.fpaycode and pm.famt<0
left join fpf_payrefund fp on fp.fpaycode = fr.frefpaycode
left join fne_unknown_capital_balance ub on ub.fpaycode = p.fpaycode
left join fne_unknown_capital uc on uc.fid = ub.funknownfundsid
where 1=1
and  p.fpaycode not in (select fpaycode from une_paybook_paycode)

and p.fchgagenidcode = '${fagenidcode}'
and up.fplaceid in (
select distinct up.fid
from uab_place up
left join uab_place_user upu
on up.fid = upu.fplaceid
where up.fagenidcode='${fagenidcode}'
and (upu.fuserid = '${getUser("ID")}'  or  (select fismanage from uab_place_user where fuserid = '${getUser("ID")}' )=1
or (select count(1) from uab_place_user where fuserid = '${getUser("ID")}' )=0 ))
and p.fpaydate >= '${pay_bgndate}'
and p.fpaydate <= '${pay_enddate}'
and fp.FPLANDATE >= '${bgndate}'
and fp.FPLANDATE <= '${enddate}'

and (case when ub.fpaycode is not null then p.freceiveddate else fp.freceivedate end) >= '${fre_bgndate}'
and (case when ub.fpaycode is not null then p.freceiveddate else fp.freceivedate end) <= '${fre_enddate}'

and pm.fitemidcode = '${fitemidcode}'
and (case when ub.fpaycode is not null then ub.fbankcode else fp.frecacctbankcode end) = '${fbankcode}'
and (case when ub.fpaycode is not null then uc.frecacct else fp.frecacct end) = '${frecacct}'
and substr(pm.ffundsnaturecode, 1, 1) = '${ftype}'
and 1=1
) total
group by total.fchgagenidcode,
total.fchgagencode,
total.fchgagenname,
total.fitemidcode,
total.fitemname,
total.fitemcode,
total.fsubcode,
total.fsubname

```

## 3.17 单位端单位缴款统计明细表-单位端常用-单位端

### 报表样式

![](report_images/image73.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 开票日期 | 否 | 包含起始日期和结束日期，默认为空 | ${bgndate},${enddate} | fne_paybook.ffilldate |
| 2 | 缴款日期 | 是 | 包含起始日期和结束日期，默认为本月 | ${pay_bgndate},${pay_enddate} | fne_paybook.fpaydate |
| 3 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${fre_bgndate},${fre_enddate} | fne_paybook.freceiveddate,fpf_clear_transfer.freceivedate |
| 4 | 执收单位 | 否 | 默认为空 | ${fagenidcode} | uab_place.fagenidcode,fne_paybook.fchgagenidcode |
| 5 | 收费项目 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_item.fitemidcode |
| 6 | 班级 | 否 | 默认为空 | ${class} | une_paybook.fcustom2 |
| 7 | 年级 | 否 | 默认为空 | ${grade} | une_paybook.fcustom1 |
| 8 | 缴款人姓名 | 否 | 默认为空 | ${name} | une_paybook.fpayername,fne_paybook.fpayacctname |
| 9 | 开票人 | 否 | 默认为空 | ${fauthor} | fne_paybook.fauthor |
| 10 | 缴款渠道 | 否 | 默认为空 | ${bankcode} | fne_paybook.fpaybankcode |
| 11 | 到账银行 | 否 | 默认为空 | ${fbankcode} | fne_unknown_capital_balance.fbankcode,fpf_clear_transfer.frecacctbankcode |
| 12 | 资金性质 | 否 | 默认为空 | ${ftype} | fne_paybook_item.ffundsnaturecode |
| 13 | 收款人帐号 | 否 | 默认为空 | ${frecacct} | fne_unknown_capital.frecacct,fpf_clear_transfer.frecacct |
| 14 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${p_bgndate},${p_enddate} | fpf_clear_transfer.FPLANDATE |

### 报表语句
``` SQL
/*宁夏：单位缴款统计明细表*/
select  p.fpaycode,
d.fname,
p.fchgagencode,
p.fchgagenname,
nvl(f.fimamt, pm.famt) as famt,
case when m.fisenter = '1'  or pm.famt<0 or m.fstats='9' or ucb.fbalancedate is not null then nvl(f.fimamt, pm.famt) else 0 end as freceivedamt,
ft.FPLANDATE as fpaydate,
p.fpaydate as fpaydate2,
--u.fpayername,
case when u.fpayername is null then p.fpayacctname else u.fpayername end as fpayername,
p.fauthor,
u.fcustom1,
u.fcustom2,
u.fcustom3,
u.fcustom4,
pm.fitemname,
pm.fitemcode,
p.ffilldate,
u.fcomcbillbatchcode,
fb.fbillname,
u.fcomcbillno as fbillno,
m.ftransdate,
m.ftransno,
case when ucb.fpaycode is not null then p.freceiveddate else ft.freceivedate end as fenterdate,
u.fcheckcode,
case when ucb.fpaycode is not null then uc.frecacctname else ft.frecacctname end as frecacctname,
case when ucb.fpaycode is not null then uc.frecacct else ft.frecacct end as frecacct,
case when ucb.fpaycode is not null then uc.frecacctbank else ft.frecacctopenbankname end as frecacctbank,
FSORTNO
from fne_paybook p
left join fne_paybook_item pm
on pm.fpid = p.fid
left join afa_res_dictitem d
on d.fcode = p.fpaybankcode
and d.fdictcode = '152'
left join une_paybook u
on u.fpaycode = p.fpaycode
left join fne_funddivide f
on f.fpaybooksubid = pm.fid
--and f.fclearorder = 1
left join fne_collect_to_transfer tf
on tf.ftranscollectid= f. fcollectid
left join fne_transfer_bank_msg m
on m.ftransno = tf.ftransferno
left join fpf_clear_transfer ft
on ft.fbatchno = tf.ftransferno and ft.fiscomplete = '1'
/*left join fne_clear_receipt cr on cr.fbatchno = tf.ftransferno
left join fne_refund_lock fr on fr.fdedpaycode=p.fpaycode and pm.famt<0
left join fpf_payrefund fp on fp.fpaycode = fr.frefpaycode  */
left join fne_unknown_capital_balance ucb on ucb.fpaycode = p.fpaycode
left join fne_unknown_capital uc on uc.fid = ucb.funknownfundsid
left join fab_bill fb on fb.fid = u.fbillid

where  1=1
--((pm.famt<0 and fp.fresult='1') or pm.famt>=0)

and  p.fpaycode not in (select fpaycode from une_paybook_paycode)

and p.fchgagenidcode = '${fagenidcode}'
and u.fplaceid in (
select distinct up.fid
from uab_place up
left join uab_place_user upu
on up.fid = upu.fplaceid
where up.fagenidcode='${fagenidcode}'
and (upu.fuserid = '${getUser("ID")}'  or  (select fismanage from uab_place_user where fuserid = '${getUser("ID")}' )=1
or (select count(1) from uab_place_user where fuserid = '${getUser("ID")}' )=0 ))
and p.fpaybankcode = '${bankcode}'
and ft.FPLANDATE >= '${p_bgndate}'
and ft.FPLANDATE <= '${p_enddate}'
and p.fpaydate>= '${pay_bgndate}'
and p.fpaydate<= '${pay_enddate}'
and p.fpaydate = '${fpaydate}'
and p.ffilldate >= '${bgndate}'
and p.ffilldate <= '${enddate}'
and (case when ucb.fpaycode is not null then p.freceiveddate else ft.freceivedate end) >= '${fre_bgndate}'
and (case when ucb.fpaycode is not null then p.freceiveddate else ft.freceivedate end) <= '${fre_enddate}'
-- and decode(m.fstats,'9',nvl(m.fenterdate,cr.fdate),m.fenterdate)   >= '${fre_bgndate}'
-- and decode(m.fstats,'9',nvl(m.fenterdate,cr.fdate),m.fenterdate)   <= '${fre_enddate}'
and pm.fitemidcode = '${fitemidcode}'
and u.fcustom2 like '${class}%'
and u.fcustom1 like '${grade}%'
and (u.fpayername like '${name}%' or p.fpayacctname like '${name}%')
and p.fauthor like '${fauthor}'
and (case when ucb.fpaycode is not null then ucb.fbankcode else ft.frecacctbankcode end) = '${fbankcode}'
and (case when ucb.fpaycode is not null then uc.frecacct else ft.frecacct end) = '${frecacct}'
and substr(pm.ffundsnaturecode, 1, 1) = '${ftype}'
order by p.fchgagencode, p.fpaycode, pm.fitemcode

```

## 3.18 资金收入明细表

### 报表样式

![](report_images/image76.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${bgndate},${enddate} | fpf_capital_receive.fdate |
| 2 | 帐户名称 | 否 | 默认为空 | ${frecacct} | fpf_capital_receive.frecacct |
| 3 | 记账帐号 | 否 | 默认为空 | ${frecacctname} | fpf_capital_receive.frecacctname |
| 4 | 缴款渠道 | 否 | 默认为空 | ${fconfirm} | fpf_capital_receive.fconfirm |

### 报表语句
``` SQL
select
distinct
fdate,
ftime,
famt,
frecacct,
frecacctname,
fpayername,
fmemo,
t.fconfirm as fconfirmcode,
case when t.fconfirm = 1 then '统一支付平台收入' else '其他渠道收入' end as fconfirm
from fpf_capital_receive t
join (select distinct frgncode,faccount,faccname,facctypecode from fab_acc) fac on fac.faccount = t.frecacct
join afa_org o on fac.frgncode = o.org_code and fac.facctypecode = 1
join afa_user u on o.org_id = u.main_orgid and (u.user_id =  '${getUser("ID")}'  or '${getUser("CODE")}'='system' )
where
1=1
and t.fdate >= '${bgndate}'
and t.fdate <= '${enddate}'
and t.frecacct = '${frecacct}'
and t.frecacctname= '${frecacctname}'
and t.fconfirm= '${fconfirm}'
order by fdate,ftime

```

## 3.19 单位资金划转对账表-单位端

### 报表样式

![](report_images/image78.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收单位 | 否 | 默认为空 | ${fchgagenidcode} | fne_paybook.fchgagenidcode |
| 2 | 缴款日期 | 否 | 包含起始日期和结束日期，默认为空 | ${pay_bgndate},${pay_enddate} | fne_paybook.fpaydate |
| 3 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${trans_bgndate},${trans_enddate} | fpf_clear_transfer.FPLANDATE |
| 4 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${enter_bgndate},${enter_enddate} | fne_capital_transfer.fenterdate |
| 5 | 收款帐户类型 | 否 | 默认为空 | ${frecaccttype} | fne_capital_transfer.frecaccttype |
| 6 | 结算渠道 | 否 | 默认为空 | ${fbankcode} | fne_capital_transfer.fbankcode |
| 7 | 结算批次号 | 否 | 默认为空 | ${ftransno} | fne_capital_transfer.ftransno |
| 8 | 收款帐号 | 否 | 默认为空 | ${frecacct} | fne_capital_transfer.frecacct |

### 报表语句
``` SQL
/*宁夏：单位资金划转对账表（单位端）*/
----研发提供  欧正鹏 20190401----
--修改 陈国银 20190405--
select t.ftransno,
'ZX'||substr(t.ftransno,4,6)||N10_TO_62(substr(t.ftransno,10,6)||
f_16_tr_10(substr(t.ftransno,16,7))) as fmemo,
t.frecacctname,
t.frecacct,
case  t.frecaccttype
when '0' then
'虚拟账户'
when '1' then
'财政专户'
when '2' then
'汇缴专户'
when '3' then
'待解缴科目'
when '4' then
'单位监管账户'
when '5' then
'国库账户'
when '7' then
'单位清分账户'
else
'其他'
end as frecaccttype,
sum(nvl(f.fimamt, pm.famt))as famt,
b.fname,
p.fpaymentchannel,
fp.FPLANDATE as ftransferdate,
t.fenterdate,
t.fbankcode,
pm.fitemidcode
from fne_paybook p
left join fne_paybook_item pm
on pm.fpid = p.fid
left join fne_funddivide f
on pm.fid = f.fpaybooksubid
left join FNE_COLLECT_TO_TRANSFER   tf on tf.FTRANSCOLLECTID  = f.fcollectid
join fne_capital_transfer t
on t.ftransno = tf.ftransferno
left join fpf_clear_transfer fp
on fp.fbatchno = tf.ftransferno and fp.fiscomplete = '1'
left join fpf_bank b
on b.fcode = t.fbankcode
left join fab_acc ac
on t.frecacct = ac.faccount and ac.fisfinal = '1'
join afa_org oo
on oo.org_id = p.fchgagenidcode--and oo.org_type = 'AGEN'
and oo.org_id = ac.fagenidcode
join (select o.org_id, o.org_code, o.org_seq, o.org_type
from afa_org o
join afa_user u
on o.org_id = u.main_orgid
or u.user_code = 'system'
where u.user_id = '${getUser("ID")}'
--where u.user_id='913fcadd614d42758f897becafa06c4a'
) tt
on ((oo.org_seq like tt.org_seq||'%' and (tt.org_type='AGEN' or  tt.org_type='REGION'))or tt.org_code = '640000')
where fp.FPLANDATE >= '${trans_bgndate}'
and fp.FPLANDATE <= '${trans_enddate}'
and t.fenterdate >= '${enter_bgndate}'
and t.fenterdate <= '${enter_enddate}'
and p.fpaydate >= '${pay_bgndate}'
and p.fpaydate <= '${pay_enddate}'
and t.fbankcode = '${fbankcode}'
and t.frecaccttype = '${frecaccttype}'
and t.frecacct = '${frecacct}'
and t.ftransno like '${ftransno}%'
and p.fchgagenidcode = '${fchgagenidcode}'
group by t.ftransno,
t.frecacctname,
t.frecacct,
t.frecaccttype,
b.fname,
p.fpaymentchannel,
fp.FPLANDATE,
t.fenterdate,
t.fbankcode,
pm.fitemidcode
order by fp.FPLANDATE, t.fbankcode

```


## 3.20 单位资金划转对账明细表-单位端

### 报表样式

![](report_images/image80.png)

### 报表查询条件

| 序号 | 查询条件 | 是必填 | 说明 | 对应参数 | 对应表字段 |
|:----|:---:|:---:| :---: |-----|-----|
| 1 | 执收单位 | 否 | 默认为空 | ${fchgagenidcode} | fne_paybook.fchgagenidcode |
| 2 | 项目名称 | 否 | 默认为空 | ${fitemidcode} | fne_paybook_item.fitemidcode |
| 3 | 缴款日期 | 否 | 包含起始日期和结束日期，默认为空 | ${pay_bgndate},${pay_enddate} | fne_paybook.fpaydate |
| 4 | 划转日期 | 否 | 包含起始日期和结束日期，默认为空 | ${tran_bgndate},${tran_enddate} | fpf_clear_transfer.FPLANDATE |
| 5 | 到账日期 | 否 | 包含起始日期和结束日期，默认为空 | ${enter_bgndate},${enter_enddate} | fne_capital_transfer.fenterdate |
| 6 | 收款帐户类型 | 否 | 默认为空 | ${frecaccttype} | fne_capital_transfer.frecacct |
| 7 | 结算渠道 | 否 | 默认为空 | ${fbankcode} | fpf_clear_transfer.fbankcode |
| 8 | 结算批次号 | 否 | 默认为空 | ${ftransno} | fpf_clear_transfer.ftransno |
| 9 | 缴款人名称 | 否 | 默认为空 | ${fpayername} | v_une_paybook.fpayername |
| 10 | 收款银行名称 | 否 | 默认为空 | ${frecacctname} | fne_paybook.frecacctname |
| 11 | 电子缴款码 | 否 | 默认为空 | ${fpaycode} | fne_paybook.fpaycode |

### 报表语句
``` SQL
/*宁夏：单位资金划转对账明细表(单位)*/
----研发提供  欧正鹏 20190322----
/*修改：陈国银 20190328*/
/*修改黄德委20191107like太多是个隐患*/
select
p.fpaycode,
p.fchgagencode,
p.fchgagenidcode,
p.fchgagenname,
u.fbillname,
u.fcomcbillno as fbillno,
u.fpayername,
u.fcustom1,
u.fcustom2,
u.fcustom3,
u.fcustom4,
t.frecacctname,
t.frecacct,
f.fitemcode,
f.fitemname,
--pm.fitemcode,
--pm.fitemname,
--pm.famt,
nvl(f.fimamt, pm.famt) as famt,
fp.FPLANDATE as ftransdate,
t.fenterdate as fenterdate,
t.ftransno
from fne_paybook p
left join fne_paybook_item pm
on pm.fpid = p.fid
left join v_une_paybook u
on u.fpaycode = p.fpaycode
left join fne_funddivide f
on pm.fid = f.fpaybooksubid
and f.fpaycode = p.fpaycode
left join FNE_COLLECT_TO_TRANSFER   tf on tf.FTRANSCOLLECTID  = f.fcollectid
left join fne_capital_transfer t
on t.ftransno = tf.ftransferno
left join fpf_clear_transfer fp
on fp.fbatchno = tf.ftransferno and fp.fiscomplete = '1'
left join fab_acc ac
on t.frecacct = ac.faccount and ac.fisfinal = '1'
join afa_org oo
on oo.org_id = p.fchgagenidcode  --and oo.org_type = 'AGEN'
and oo.org_id = ac.fagenidcode
join (select o.org_id, o.org_code, o.org_seq, o.org_type
from afa_org o
join afa_user u
on o.org_id = u.main_orgid
where u.user_id = '${getUser("ID")}'
--where u.user_id='913fcadd614d42758f897becafa06c4a'
) tt
on ((oo.org_seq like tt.org_seq||'%' and (tt.org_type='AGEN' or  tt.org_type='REGION'))or tt.org_code = '640000')
where fp.FPLANDATE >= '${tran_bgndate}'
and fp.FPLANDATE <= '${tran_enddate}'
and t.fenterdate >= '${enter_bgndate}'
and t.fenterdate <= '${enter_enddate}'
and ft.freceivedate  >= '${fre_bgndate}'
and ft.freceivedate  <= '${fre_enddate}'
and p.fpaydate >= '${pay_bgndate}'
and p.fpaydate <= '${pay_enddate}'
and t.fbankcode = '${fbankcode}'
and t.frecaccttype = '${frecaccttype}'
and t.ftransno like '${ftransno}%'
and p.fchgagenidcode = '${fchgagenidcode}'
and u.fpayername like '${fpayername}%'
and p.frecacctname like '${frecacctname}'
and p.fpaycode like '${fpaycode}%'
and pm.fitemidcode = '${fitemidcode}'
order by fp.FPLANDATE,t.fbankcode

```

