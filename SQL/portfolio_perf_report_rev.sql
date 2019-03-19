--drop table EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO;
--drop table EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PRICES;
--drop table EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PERF;
--
--
--CREATE TABLE EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO
--(
--    CUSIP           VARCHAR2(10 BYTE),
--    MD_SECURITY_ID  NUMBER,
--    SEDOL           VARCHAR2(10 BYTE),
--    TICKER          VARCHAR2(20 BYTE),
--    SEC_NAME        VARCHAR2(100 BYTE),
--    ASSET_TYPE      VARCHAR2(30 BYTE),
--    SECURITY_TYPE   VARCHAR2(30 BYTE),
--    SECTOR          VARCHAR2(30 BYTE),
--    COUNTRY         VARCHAR2(30 BYTE),
--    INV_QTY         NUMBER
--);
--
--CREATE TABLE EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PRICES
--(
--    MD_SECURITY_ID  NUMBER,
--    VALUE_DATE      DATE,
--    PRICE           NUMBER
--);
--
--CREATE TABLE EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PERF
--(
--    BUSINESS_DATE   DATE,
--    MD_SECURITY_ID  NUMBER,
--    PRICE           NUMBER,
--    INV_QTY         NUMBER,
--    INV_VAL         NUMBER,
--    UTILIZATION     NUMBER,
--    LOAN_QTY        NUMBER,
--    LOAN_VAL        NUMBER,
--    FEE             NUMBER
--);
--
--commit;

--select * from EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO


--Clear the tables
--truncate table EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO
--truncate table EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PRICES
--truncate table EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PERF
--select sum(inv_qty) from EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO
--select * from EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PERF
--
--
SELECT *
FROM FIDELITY_WHATIF_PFOLIO
WHERE cusip = '820017101'
--and client = 'FSCH'
--
--select * from md_security
--where cusip = '923725105'
--
--
--select client, cusip, count(*)
--from (
--select distinct client, cusip, md_security_id
--from FIDELITY_WHATIF_PFOLIO
--where md_security_id is not null
--)
--group by client,cusip
--having count(*) > 1
--order by cusip
--
--
--60671Q104
--656844107
--71377G100
--923725105


--Copy the portfolio details from the Load table (pre-populated by the TOAD import function)
INSERT INTO FIDELITY_WHATIF_PFOLIO (cusip, md_security_id, sedol, ticker, sec_name, asset_type, security_type, sector, country, inv_qty)
  SELECT
    p.cusip,
    s.md_security_id,
    s.sedol,
    s.ticker,
    s.security_description,
    s.asset_type,
    s.asset_class,
    s.sector_name,
    c.country_name,
    sum(p.inv_qty)
  FROM FIDELITY_WHATIF_PFOLIO_LOAD p
    LEFT JOIN (
                SELECT
                  sec.*,
                  CASE
                  WHEN it.asset_type_cd = 'EQ'
                    THEN sec.exchange_country_cd
                  ELSE sec.issue_country_cd
                  END                     AS country_cd,
                  CASE
                  WHEN it.asset_type_cd = 'FI'
                    THEN 'Fixed Income'
                  WHEN it.asset_type_cd = 'EQ'
                    THEN 'Equity'
                  END                     AS asset_type,
                  it.instrument_type_desc AS asset_class,
                  idc.sector_name,
                  idc.sub_industry_name
                FROM md_security sec
                  INNER JOIN instrument_type it ON sec.instrument_type_cd = it.instrument_type_cd
                  LEFT JOIN idc_gics_codes idc ON sec.industry_cd = idc.sub_industry_id
              ) s ON (p.cusip = s.cusip AND s.primary_issue = 'Y')
    LEFT JOIN country c ON s.country_cd = c.country_cd
  GROUP BY p.cusip,
    s.md_security_id,
    s.sedol,
    s.ticker,
    s.security_description,
    s.asset_type,
    s.asset_class,
    s.sector_name,
    c.country_name;

--Find any duplicate CUSIPs
SELECT
  cusip,
  count(*)
FROM (
  SELECT DISTINCT
    md_security_id,
    cusip
  FROM EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO
)
GROUP BY cusip
HAVING count(*) > 1

SELECT *
FROM md_security
WHERE cusip IN ('00972D105')
ORDER BY cusip

SELECT *
FROM EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO
WHERE cusip IN ('51817R106', '923725105', '876568502', '00972D105', '32095101', 'Y6366T112', '09202G101')
ORDER BY cusip


--Workaround required because of duplicate securities with the same CUSIP
DELETE FROM EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO
WHERE md_security_id IN (352671);

COMMIT

SELECT max(business_date)
FROM md_result



     --Store security prices to simplify the queries later
     DECLARE
p_value_date DATE := '12 May 2015';
p_end_date DATE := '11 Jul 2015';
BEGIN
  WHILE p_value_date <= p_end_date LOOP

    --Lendable value and value of securities on loan
    INSERT INTO EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PRICES (MD_SECURITY_ID, VALUE_DATE, PRICE)
      SELECT
        s.md_security_id,
        p_value_date,
        sp.PRICE * fx.value AS price
      FROM (
             SELECT DISTINCT md_security_id
             FROM EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO
           ) s
        INNER JOIN (
                     SELECT
                       spi.*,
                       spi.currency_cd || 'USD' AS fx_cd
                     FROM md_security_price spi
                   ) sp ON s.md_security_id = sp.md_security_id
        INNER JOIN dsx_currency fx ON sp.fx_cd = fx.fx_cd
      WHERE sp.VALUE_DATE = (SELECT max(value_date)
                             FROM md_security_price
                             WHERE md_security_id = s.md_security_id AND value_date <= p_value_date)
            AND fx.VALUE_DATE = (SELECT max(value_date)
                                 FROM dsx_currency
                                 WHERE fx_cd = sp.fx_cd AND value_date <= p_value_date);

    COMMIT;

    p_value_date := p_value_date + 1;

  END LOOP;

END;


SELECT
  value_date,
  count(*)
FROM EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PRICES
GROUP BY value_date
ORDER BY value_date


--Find the minimum date that data exists for within the md_result_details table
SELECT business_date
FROM md_result
WHERE result_id = (SELECT min(result_id)
                   FROM md_result_details);

MISS THIS NEXT STEP

--Store security prices to simplify the queries later 
DECLARE
  p_date      DATE := '01 Jun 2016';
  p_bus_date  DATE := '01 Jun 2016';
  p_end_date  DATE := '01 Jul 2016';
  p_dayofweek VARCHAR2(10 BYTE);
BEGIN

  WHILE p_date <= p_end_date LOOP

    p_dayofweek := trim(to_char(to_date(p_date, 'dd-mon-yy'), 'DAY'));

    p_bus_date := CASE WHEN p_dayofweek = 'SATURDAY'
      THEN p_date - 1
                  WHEN p_dayofweek = 'SUNDAY'
                    THEN p_date - 2
                  ELSE p_date END;

    --Lendable value and value of securities on loan
    INSERT INTO EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PERF (BUSINESS_DATE, CLIENT, MD_SECURITY_ID, PRICE, INV_QTY, INV_VAL, UTILIZATION, LOAN_QTY, LOAN_VAL, FEE)
      SELECT
        p_date,
        p.client,
        p.md_security_id,
        sp.price,
        p.inv_qty,
        p.inv_qty * (CASE WHEN asset_type = 'Fixed Income'
          THEN SP.PRICE / 100
                     ELSE sp.price END)                           AS inv_val,
        RD.util,
        round(p.inv_qty * rd.util / 100, 0)                       AS loan_qty,
        round(p.inv_qty * rd.util / 100, 0) * (CASE WHEN asset_type = 'Fixed Income'
          THEN SP.PRICE / 100
                                               ELSE sp.price END) AS loan_val,
        RD.avg_spread_all_amt                                     AS fee
      FROM EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO p
        INNER JOIN EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PRICES sp ON P.MD_SECURITY_ID = sp.MD_SECURITY_ID
        LEFT JOIN (
                    SELECT
                      d.*,
                      CASE WHEN loan_qty_amt IS NULL
                        THEN 0
                      ELSE utilization END AS util
                    FROM md_result_details_arch d
                    WHERE result_id = (SELECT max(result_id)
                                       FROM md_result
                                       WHERE business_date = p_bus_date)
                  ) rd ON p.md_security_id = rd.md_security_id
      WHERE sp.VALUE_DATE = p_date;

    COMMIT;

    p_date := p_date + 1;

  END LOOP;

END;

DO THIS ONE

--Extract result data from MD_RESULT_DETAILS 
DECLARE
  p_date      DATE := '01 Jun 2016';
  p_bus_date  DATE := '01 Jun 2016';
  p_end_date  DATE := '01 Jul 2016';
  p_dayofweek VARCHAR2(10 BYTE);
BEGIN

  WHILE p_date <= p_end_date LOOP

    p_dayofweek := trim(to_char(to_date(p_date, 'dd-mon-yy'), 'DAY'));

    p_bus_date := CASE WHEN p_dayofweek = 'SATURDAY'
      THEN p_date - 1
                  WHEN p_dayofweek = 'SUNDAY'
                    THEN p_date - 2
                  ELSE p_date END;

    --Lendable value and value of securities on loan
    INSERT INTO EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PERF (BUSINESS_DATE, MD_SECURITY_ID, PRICE, INV_QTY, INV_VAL, UTILIZATION, LOAN_QTY, LOAN_VAL, FEE)
      SELECT
        p_date,
        p.md_security_id,
        sp.price,
        p.inv_qty,
        p.inv_qty * (CASE WHEN asset_type = 'Fixed Income'
          THEN SP.PRICE / 100
                     ELSE sp.price END)                           AS inv_val,
        RD.util,
        round(p.inv_qty * rd.util / 100, 0)                       AS loan_qty,
        round(p.inv_qty * rd.util / 100, 0) * (CASE WHEN asset_type = 'Fixed Income'
          THEN SP.PRICE / 100
                                               ELSE sp.price END) AS loan_val,
        RD.avg_spread_all_amt                                     AS fee
      FROM EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO p
        INNER JOIN EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PRICES sp ON P.MD_SECURITY_ID = sp.MD_SECURITY_ID
        LEFT JOIN (
                    SELECT
                      d.*,
                      CASE WHEN loan_qty_amt IS NULL
                        THEN 0
                      ELSE utilization END AS util
                    FROM md_result_details d
                    WHERE result_id = (SELECT max(result_id)
                                       FROM md_result
                                       WHERE business_date = p_bus_date)
                  ) rd ON p.md_security_id = rd.md_security_id
      WHERE sp.VALUE_DATE = p_date;

    COMMIT;

    p_date := p_date + 1;

  END LOOP;

END;

--Revenue Trending
SELECT
  business_date,
  sum(loan_val * fee / 10000 / 365) AS revenue
FROM FIDELITY_WHATIF_PFOLIO_PERF pp1
GROUP BY business_date
ORDER BY business_date


--Performance Summary
SELECT
  count(DISTINCT md_security_id)               AS security_count,
  sum(inv_val) / count(DISTINCT business_date) AS inv_val,
  sum(loan_val) / sum(inv_val) * 100           AS utilization,
  sum(loan_val * fee) / sum(loan_val)          AS fee,
  sum(loan_val * fee / 10000 / 365)            AS revenue
FROM FIDELITY_WHATIF_PFOLIO_PERF


--Inventory breakdown by Asset Class
SELECT
  P.SECURITY_TYPE,
  sum(inv_val) / count(DISTINCT business_date) AS avg_inv_val
FROM FIDELITY_WHATIF_PFOLIO p
  LEFT JOIN (
              SELECT *
              FROM FIDELITY_WHATIF_PFOLIO_PERF
              --                where   business_date = '31 Jan 2015'
            ) pp ON p.md_security_id = pp.md_security_id
WHERE p.md_security_id IS NOT NULL
GROUP BY p.security_type
ORDER BY p.security_type


--Top Revenue Earners
SELECT *
FROM (
  SELECT
    P.SEC_NAME,
    CASE WHEN sum(pp.loan_val) = 0
      THEN 0
    ELSE sum(pp.loan_val * pp.fee) / sum(pp.loan_val) END AS fee,
    sum(pp.inv_val) / count(DISTINCT business_date)       AS daily_inv_val,
    sum(pp.loan_val) / count(DISTINCT business_date)      AS daily_loan_val,
    sum(pp.loan_val * pp.fee / 10000 / 365)               AS revenue
  FROM FIDELITY_WHATIF_PFOLIO p
    INNER JOIN FIDELITY_WHATIF_PFOLIO_PERF pp ON p.md_security_id = pp.md_security_id
  WHERE PP.MD_SECURITY_ID IS NOT NULL
  GROUP BY p.SEC_NAME
)
ORDER BY revenue DESC NULLS LAST


--Security Type Performance
SELECT
  P.SECURITY_TYPE,
  sum(pp.loan_val) / sum(pp.inv_val) * 100     AS util,
  sum(pp.loan_val * pp.fee) / sum(pp.loan_val) AS fee,
  sum(pp.loan_val * pp.fee) / sum(pp.inv_val)  AS rtl,
  sum(pp.loan_val * pp.fee / 10000 / 365)      AS revenue
FROM FIDELITY_WHATIF_PFOLIO p
  INNER JOIN FIDELITY_WHATIF_PFOLIO_PERF pp ON p.md_security_id = pp.md_security_id
WHERE PP.MD_SECURITY_ID IS NOT NULL
GROUP BY p.SECURITY_TYPE
ORDER BY p.SECURITY_TYPE


--Sector Performance
SELECT
  nvl(P.SECTOR, 'Unclassified')                AS SECTOR,
  sum(pp.loan_val) / sum(pp.inv_val) * 100     AS util,
  sum(pp.loan_val * pp.fee) / sum(pp.loan_val) AS fee,
  sum(pp.loan_val * pp.fee) / sum(pp.inv_val)  AS rtl,
  sum(pp.loan_val * pp.fee / 10000 / 365)      AS revenue
FROM FIDELITY_WHATIF_PFOLIO p
  INNER JOIN FIDELITY_WHATIF_PFOLIO_PERF pp ON p.md_security_id = pp.md_security_id
WHERE PP.MD_SECURITY_ID IS NOT NULL
--and         p.SECTOR IS NULL
GROUP BY SECTOR
ORDER BY SECTOR


--Security Level
SELECT *
FROM (
  SELECT
    P.SEC_NAME,
    sum(pp.inv_val) / count(DISTINCT business_date)       AS daily_inv_val,
    sum(pp.loan_val) / count(DISTINCT business_date)      AS daily_loan_val,
    sum(pp.loan_val) / sum(pp.inv_val) * 100              AS util,
    CASE WHEN sum(pp.loan_val) = 0
      THEN 0
    ELSE sum(pp.loan_val * pp.fee) / sum(pp.loan_val) END AS fee,
    sum(pp.loan_val * pp.fee) / sum(pp.inv_val)           AS rtl,
    sum(pp.loan_val * pp.fee / 10000 / 365)               AS revenue
  FROM FIDELITY_WHATIF_PFOLIO p
    INNER JOIN FIDELITY_WHATIF_PFOLIO_PERF pp ON p.md_security_id = pp.md_security_id
  WHERE PP.MD_SECURITY_ID IS NOT NULL
  GROUP BY p.SEC_NAME
)
ORDER BY revenue DESC NULLS LAST


--Unrecognised Securities
SELECT
  l.cusip,
  l.sec_name,
  sum(l.inv_qty) AS inv_qty
FROM EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_LOAD l
  INNER JOIN EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO p ON l.cusip = p.cusip
WHERE p.md_security_id IS NULL
GROUP BY l.cusip,
  l.sec_name
ORDER BY l.cusip

--Could Not Price
SELECT *
FROM (
  SELECT
    p.cusip,
    min(p.inv_qty)  AS inv_qty,
    sum(CASE WHEN PF.PRICE IS NOT NULL
      THEN 1
        ELSE 0 END) AS price_count
  FROM EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO p
    LEFT JOIN EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PERF pf ON P.MD_SECURITY_ID = PF.MD_SECURITY_ID
  WHERE p.md_security_id IS NOT NULL
  GROUP BY p.cusip
)
ORDER BY price_count

--Percentage Not On Loan
SELECT
  business_date,
  count(*)        AS sec_count,
  sum(pf.inv_val) AS inv_val,
  sum(CASE WHEN PF.LOAN_QTY = 0
    THEN 1
      ELSE 0 END) AS Unutilised_Secs,
  sum(CASE WHEN PF.LOAN_QTY = 0
    THEN pf.inv_val
      ELSE 0 END) AS Unutilised_Inv_Val
FROM EQMRKS_ANA.FIDELITY_WHATIF_PFOLIO_PERF pf
GROUP BY business_date
ORDER BY business_date
