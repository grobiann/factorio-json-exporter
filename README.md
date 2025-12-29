# Factorio Lua to JSON Exporter

Lua 데이터 파일(예: Factorio 모드의 items.lua)을 JSON 형식으로 변환하는 Python 프로그램입니다.

## 기능

- Lua `data:extend()` 호출에서 데이터 추출
- Lua 테이블 구조를 Python 딕셔너리로 파싱
- JSON 형식으로 변환 및 저장
- **폴더 재귀 처리**: 폴더를 선택하면 하위 폴더의 모든 .lua 파일을 자동으로 변환
- **폴더 구조 유지**: 출력 시 원본 폴더 구조를 그대로 유지
- GUI 파일/폴더 선택 대화상자 지원
- 커맨드라인 인터페이스 지원

## 사용 방법

### GUI 모드

#### 기본 모드 (폴더 선택 - 권장)

```bash
python lua_to_json.py
```

프로그램을 실행하면:
1. **폴더 선택 창**이 나타납니다 (예: `prototypes` 폴더)
2. 선택한 폴더와 하위 폴더의 모든 .lua 파일을 검색합니다
3. JSON 파일을 저장할 출력 폴더를 선택합니다 (예: `output` 폴더)
4. 원본 폴더 구조를 유지하면서 변환합니다
   - 예: `prototypes/items/ammo.lua` → `output/items/ammo.json`

#### 개별 파일 선택 모드

```bash
python lua_to_json.py --files
```

개별 파일을 선택하여 변환하려면 `--files` 옵션을 사용합니다.

### 커맨드라인 모드

```bash
python lua_to_json.py <경로1> <경로2> ... [-o 출력폴더]
```

경로는 파일 또는 폴더가 될 수 있습니다.

예시:

```bash
# 폴더 전체를 재귀적으로 변환 (폴더 구조 유지)
python lua_to_json.py prototypes -o output

# 여러 폴더를 한 번에 변환
python lua_to_json.py prototypes data/recipes -o output

# 개별 파일 변환
python lua_to_json.py items.lua recipes.lua -o output

# 출력 폴더를 지정하지 않으면 원본 파일 옆에 생성
python lua_to_json.py prototypes
```

### 폴더 구조 예시

입력 구조:
```
prototypes/
  ├── items/
  │   ├── ammo.lua
  │   └── armor.lua
  └── recipes/
      └── crafting.lua
```

실행: `python lua_to_json.py prototypes -o output`

출력 구조:
```
output/
  ├── items/
  │   ├── ammo.json
  │   └── armor.json
  └── recipes/
      └── crafting.json
```

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
