# EXP-GPKM-001 — GP Korea Match 수동 검증 실험

- 상태: **PROPOSED — CEO/OS gate required**
- 기록일: 2026-08-10
- Domain: OEM
- Risk: HIGH
- 민감 플래그: `money_pricing`, `external_permission_change`
- 결정 참조: [DEC-GPKM-001](../decisions/DEC-GPKM-001-gp-korea-match-hold.md)
- 검증 참조: [VAL-GPKM-001](../validations/VAL-GPKM-001-gp-korea-match.md)

## 목적

단순 한국 Supplier 검색이 아닌 `private / verified buyer mandate`가
Korean Supplier가 비용을 지불할 만큼 구별되는 제안인지 검증한다. 이 실험은
**한 개 Vertical**만 대상으로 하며, 플랫폼을 만들지 않는다.

## 검증 가설

1. 100건의 raw demand 중 실제 구매 조건을 구조화할 수 있는 수요가 존재한다.
2. 20개 Supplier dry-run에서 MOQ·인증·수출경험·대응 가능성의 최소 검증이
   반복 가능하다.
3. Korean Supplier 10곳이 GP의 success-fee 구조와 지급 조건을 읽고
   **서면으로 동의**한다.
4. Buyer 10곳이 GP에 비공개 소싱/소개를 맡기는 **명시적 sourcing mandate**를
   제공한다.
5. 단계별 human time의 median과 p90가 목표 **10분/RFQ**를 향해 개선 가능한지
   측정할 수 있다. 초기 20–60분 추정은 성공으로 간주하지 않는다.

## 최소 실행 단위

| 작업 | 표본/완료 기준 | 기록할 안전한 메타데이터 |
|---|---|---|
| Demand screening | 단일 Vertical의 raw demand 100건 | 유효/무효 사유 코드, 조건 완전성, 소스 유형 |
| Supplier dry-run | 적합 Supplier 20곳 | capability 확인 상태, match 사유 코드, 응답 상태 |
| Supplier fee validation | Supplier 10곳 | 수수료 구조 서면 동의/거절/보류 코드; 실제 가격·연락처는 미기록 |
| Buyer mandate validation | Buyer 10곳 | mandate 동의/거절/보류 코드; 실제 신원·구매 세부는 미기록 |
| Time study | 모든 단계 | 단계별 시작/종료 시각, 사람 개입 사유 코드, 총 human minutes |

## Guardrails

- 플랫폼, 공개 Marketplace, 공급사/Buyer 데이터베이스 제품을 개발하지 않는다.
- Buyer 또는 Supplier의 신원을 서로에게 공개하거나 직접 소개하기 전 각 당사자의
  명시적 동의를 확인한다.
- tradeKorea/KOTRA 등 제3자 데이터는 각 서비스의 약관과 접근 권한을 확인한
  범위에서 수동 검토한다. 자동 수집·대량 복제·재판매는 하지 않는다.
- 제조·재고·물류·결제·품질보증·계약 체결의 책임을 GP가 인수하지 않는다.
- 실제 가격 제안, 수수료 조건 확정, 외부 동의 수집은 CEO/OS 승인 후에만 진행한다.

## Hard Kill 조건

다음 중 하나가 확인되면 플랫폼 개발 또는 확장 실험을 중단하고 KILL 검토로
전환한다.

1. 단일 Vertical의 demand 100건에서 유효하고 접촉 가능한 mandate가 부족해
   반복 가능한 sourcing 기회가 형성되지 않는다.
2. Supplier 10곳 중 필요한 수준의 서면 수수료 동의가 나오지 않거나, 동의가
   실질적으로 5% 구조를 거부한다.
3. Buyer 10곳에서 private/verified sourcing mandate가 확보되지 않는다.
4. 필요한 검증을 모두 포함한 human time이 자동화 반복 후에도 목표 10분/RFQ에
   수렴할 경로를 보이지 않는다.
5. 이용약관·접근권한·개인정보/소개 동의 요건 때문에 합법적이고 재현 가능한
   demand 또는 supplier 검증 경로를 만들 수 없다.
6. GP가 수수료를 받기 위해 제조, 품질, 물류, 결제 또는 계약 책임을 떠안아야만
   하는 구조임이 드러난다.

## 성공 후 다음 결정

성공은 곧 플랫폼 개발 승인이 아니다. 위 가설과 Hard Kill 조건에 대한 증거를
첨부해 CEO/OS에 다음 중 하나를 요청한다: `HOLD 유지`, `제한된 수동 서비스
파일럿 승인`, 또는 `KILL`. 제품 개발은 별도 Decision 없이는 시작하지 않는다.
