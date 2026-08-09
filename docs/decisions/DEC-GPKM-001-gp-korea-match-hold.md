# DEC-GPKM-001 — GP Korea Match: HOLD 및 검증 우선

- 상태: **ACTIVE — HOLD**
- 기록일: 2026-08-10
- 결정자: AJ / GP Company (사업검증 결과 기록)
- 판정: **58 / 100**
- 적용 범위: GP Korea Match의 신규 사업 검증 및 관련 실험
- 관련 기록: [VAL-GPKM-001](../validations/VAL-GPKM-001-gp-korea-match.md), [EXP-GPKM-001](../experiments/EXP-GPKM-001-gp-korea-match.md)

## 결정

GP Korea Match는 **HOLD**로 둔다. 시장·지불의향의 핵심 가설이 아직
검증되지 않았으므로, 제품 또는 공개 Marketplace의 개발을 시작하지 않는다.

다음은 실험 범위에서 검증할 수 있다.

- 한국 공급사가 검증된 해외 구매 기회에 대해 수수료를 지불할 의향이 있는지
- 해외 Buyer가 익명화된 한국 공급사 후보 대신, 검증·비공개 소싱 mandate를
  GP에 맡길 의향이 있는지
- 수작업 시간이 AI 보조로 목표치에 수렴할 수 있는지

## 운영 경계

- **플랫폼 개발 금지:** 수수료 동의, Buyer mandate, 반복 가능한 처리시간이
  실증되기 전에는 DB·Marketplace·자동 매칭 제품을 개발하지 않는다.
- **Private/verified buyer mandate:** 유료 차별점은 단순 한국 공급사 검색이
  아니라 검증된 Buyer의 구체적 mandate를 비공개로 공급사에 전달하는 것이다.
- **Payer 우선순위:** 첫 payer 가설은 해외 Buyer가 아니라 **Korean Supplier**다.
- **수수료 가설:** 거래금액의 5% success fee는 시장에서 가능한 방식일 수
  있으나, GP의 실제 지불의향은 아직 입증되지 않았다.
- **데이터 경계:** tradeKorea/KOTRA 등 공개 서비스의 데이터는 출처·이용약관·
  접근 통제를 확인한 범위에서만 사용한다. 자동 수집, 재배포, 비공개 DB 구축을
  기본값으로 두지 않는다.

## 재검토 조건

`EXP-GPKM-001`이 다음을 모두 충족하고 Hard Kill 조건을 피하면 CEO/OS
검토로 올린다. 하나라도 충족하지 못하면 사업 확장 또는 플랫폼 개발 대신
KILL/보류 결정을 재검토한다.
