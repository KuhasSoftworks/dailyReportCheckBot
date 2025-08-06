# Discord 주간보고 봇

이 저장소는 **오후 6시부터 자정(KST) 사이**에 지정된 디스코드 채널에
새 메시지가 작성되었는지 확인하고, 작성하지 않은 멤버에게 알림을 보내는
파이썬 봇 스크립트를 담고 있습니다.

![dailyReportCheckBotImg.png](dailyReportCheckBotImg.png)

## 주요 기능

- **자동 점검**  
  매일 00:05(KST)에 실행되어 전날 18:00~24:00 사이 메시지를 검사합니다.
- **미제출자 알림**  
  보고를 작성하지 않은 멤버를 채널에서 멘션하고, 선택적으로 DM으로도
  리마인드를 보냅니다.
- **원‑샷 모드** (`--once`)  
  한 번만 점검 후 종료합니다. GitHub Actions 등 스케줄러에서 사용하기 좋습니다.
- **상주 모드**  
  별도 옵션 없이 실행하면 봇이 계속 온라인 상태로 유지되며, 내부 스케줄러로
  매일 점검을 수행합니다.

## 사용 방법

1. (가상환경 권장) 의존성 설치

   ```bash
   pip install -r requirements.txt
   ```

2. `.env.example`을 복사하여 `.env`를 만들고 **봇 토큰**과
   **보고 채널 ID**를 입력합니다.

   ```bash
   cp .env.example .env
   # .env 파일을 열어 DISCORD_TOKEN 과 REPORT_CHANNEL_ID 값을 설정
   ```

3. 봇 실행

   - **상주 모드**

     ```bash
     python bot.py
     ```

   - **원‑샷 모드**

     ```bash
     python bot.py --once
     ```

## GitHub Actions로 스케줄 실행

`.github/workflows/report_check.yml` 예시 워크플로가 포함되어 있습니다.
이 워크플로는 매일 00:05(KST)에 `--once` 모드로 봇을 실행합니다.

- 레포지토리 **Settings ▸ Secrets ▸ Actions**에서  
  `DISCORD_TOKEN`, `REPORT_CHANNEL_ID` 두 개의 시크릿을 등록하세요.

## 라이선스

MIT License 하에 배포됩니다. 자세한 내용은 `LICENSE` 파일을 참고하세요.