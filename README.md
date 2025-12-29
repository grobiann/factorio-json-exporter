# Factorio Lua to JSON Exporter

Lua 데이터 파일(예: Factorio 모드의 items.lua)을 JSON 형식으로 변환하는 Python 프로그램입니다.

## 기능

- Lua `data:extend()` 호출에서 데이터 추출
- Lua 테이블 구조를 Python 딕셔너리로 파싱
- JSON 형식으로 변환 및 저장
- GUI 파일 선택 대화상자 지원
- 커맨드라인 인터페이스 지원

## 사용 방법

### GUI 모드 (파일 선택 창)

```bash
python lua_to_json.py
```

프로그램을 실행하면:
1. 변환할 Lua 파일을 선택하는 창이 나타납니다
2. JSON 파일을 저장할 출력 폴더를 선택하는 창이 나타납니다 (취소하면 입력 파일과 같은 폴더에 저장)

### 커맨드라인 모드

```bash
python lua_to_json.py <파일경로1> <파일경로2> ...
```

예시:
```bash
# 입력 파일과 같은 폴더에 저장
python lua_to_json.py items.lua recipes.lua

# 특정 출력 폴더에 저장
python lua_to_json.py items.lua recipes.lua -o output_folder
python lua_to_json.py items.lua --output C:\output
```

## 출력

각 Lua 파일에 대해 같은 이름의 JSON 파일이 생성됩니다:
- `items.lua` → `items.json`
- `recipes.lua` → `recipes.json`

출력 위치:
- **GUI 모드**: 선택한 출력 폴더 (또는 입력 파일과 같은 폴더)
- **커맨드라인 모드**: `-o` 옵션으로 지정한 폴더 (또는 입력 파일과 같은 폴더)

## 요구사항

- Python 3.8 이상
- 표준 라이브러리만 사용 (외부 의존성 없음)

## 지원되는 Lua 구조

- `data:extend({ ... })` 패턴
- Lua 테이블 (딕셔너리 및 배열)
- 문자열 (작은따옴표, 큰따옴표)
- 숫자 (정수, 실수)
- 불리언 (true, false)
- nil 값
- 중첩된 테이블
- 주석 (한 줄, 여러 줄)

## 예시

입력 파일 (items.lua):
```lua
data:extend({
  {
    type = "item",
    name = "kr-biomass",
    icon = "__Krastorio2Assets__/icons/items/biomass.png",
    fuel_value = "2MJ",
    stack_size = 200,
  }
})
```

출력 파일 (items.json):
```json
[
  {
    "type": "item",
    "name": "kr-biomass",
    "icon": "__Krastorio2Assets__/icons/items/biomass.png",
    "fuel_value": "2MJ",
    "stack_size": 200
  }
]
```

## 라이선스

MIT License
