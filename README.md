# 도수치료 진료 기록지 입력 도우미

2026년 7월 1일부터 시행 중인 **도수치료 관리급여** 기준에 따라 진료 기록지에 입력해야 하는
항목들을 마우스 클릭 위주로 빠르게 작성할 수 있게 도와주는 Windows 프로그램입니다.

## 화면 구성

프로그램을 열면 화면이 **좌우 반반**으로 나뉩니다.

- **왼쪽**: 각 항목을 마우스로 클릭/선택
- **오른쪽**: 선택한 내용이 아래 양식대로 문장으로 자동 생성
- **오른쪽 하단**: `📋 전체 복사` 버튼 → 클릭 후 진료 차트에 붙여넣기(Ctrl+V)만 하면 끝

생성되는 양식 예시:

```
진단명 : M75.1 회전근개증후군
치료목적 : 통증 감소 및 자세 교정
시행자 : 홍길동 물리치료사
시행일시 : 2026년 07월 01일
시행횟수 : 1회차
시행부위 : 허리
시행기법 : Myofascial Release, Stabilization Exercise
치료시간 : 30분
```

## 왼쪽 화면 항목별 기능

| 항목 | 입력 방법 |
|---|---|
| ① 진단명 | 직접 입력 또는 내장된 근골격계 KCD 진단명 목록에서 검색 후 클릭 |
| ② 치료목적 | 통증 감소 / 자세 교정 / 관절가동범위 개선 / 근력 강화 / 기능 회복 체크박스 (+직접 추가 가능) |
| ③ 시행자 | 치료사 이름을 한 번 등록해두면, 드롭다운 화살표 클릭 → 이름 선택 → "OOO 물리치료사" 자동 입력 |
| ④ 시행일시 | 달력에서 날짜 클릭 → "OOOO년 OO월 OO일" 자동 입력 |
| ⑤ 시행횟수 | 숫자만 입력 (자동으로 "N회차" 표기) |
| ⑤ 시행부위 | 직접 입력 |
| ⑤ 치료시간 | 기본 30분 (숫자만 수정 가능) |
| ⑥ 시행기법 | Myofascial Release / Stabilization Exercise / Stretching / Joint Mobilization / Soft Tissue Mobilization 체크박스 (+직접 추가 가능) |
| ⑦ 치료 효과 평가 | 추후 업데이트 예정 (보류) |

## EXE 파일 받는 방법

이 저장소에 코드가 push 될 때마다 GitHub이 자동으로 Windows용 EXE를 빌드합니다.

1. GitHub 저장소의 **Actions** 탭 클릭
2. 가장 최근의 **Build Windows EXE** 실행 클릭
3. 하단 **Artifacts**에서 `TherapyChart-exe` 다운로드 → 압축 해제
4. `TherapyChart.exe`를 병원 컴퓨터 **바탕화면**에 복사해두고 더블클릭으로 실행

> 처음 실행 시 Windows SmartScreen 경고가 뜨면 "추가 정보 → 실행"을 누르면 됩니다.
> (서명되지 않은 프로그램에 대한 일반적인 경고입니다.)

## 데이터 저장 위치

- **치료사 이름 목록**: EXE와 같은 폴더의 `therapy_chart_settings.json`에 자동 저장됩니다.
  (해당 폴더에 쓰기 권한이 없으면 사용자 홈 폴더에 저장)
- **진단명 목록 확장**: EXE와 같은 폴더에 `diagnoses.txt` 파일을 만들고 한 줄에 하나씩
  `코드 진단명` 형식(예: `M75.1 회전근개증후군`)으로 적어두면, 내장 목록 대신 그 목록을 사용합니다.
  심평원(KCD) 전체 상병 목록을 넣고 싶을 때 이 방법을 쓰면 됩니다.

## 개발자용: 직접 실행/빌드

```bash
# 실행 (Windows, Python 3.10+ / tkinter 내장)
python therapy_chart.py

# EXE 빌드
pip install pyinstaller
pyinstaller --onefile --windowed --name TherapyChart therapy_chart.py
# → dist/TherapyChart.exe 생성
```
