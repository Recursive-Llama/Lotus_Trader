# PM v4 Uptrend Test Suite

Test suite for PM v4 Uptrend System following the comprehensive testing plan.

## Test Organization

### Layer 1: Component Testing
- **Unit Tests** (`tests/unit/`): Test individual modules in isolation
- **Integration Tests** (`tests/integration/`): Test how components work together

### Layer 2: Flow Testing
- **Flow Tests** (`tests/flow/`): Follow packets through entire pipeline using existing IDs/queries

## Running Tests

### Run all tests
```bash
pytest src/tests/ -v
```

### Run by layer
```bash
# Component tests (Layer 1)
pytest src/tests/unit/ -v
pytest src/tests/integration/ -v

# Flow tests (Layer 2)
pytest src/tests/flow/ -v -m flow
```

### Run specific test
```bash
pytest src/tests/unit/test_bucket_vocabulary.py -v
pytest src/tests/flow/test_scenario_1b_learning_loop.py -v
```

### Run with coverage
```bash
pytest src/tests/ --cov=src --cov-report=html
```

## Test Environment Setup

Before running flow tests, ensure:
1. Test database created and configured
2. All schemas applied
3. Test data seeded (tokens, curators, OHLC data)
4. Test wallet configured with $15-25 USDC
5. Environment variables set:
   - `TEST_SUPABASE_URL`
   - `TEST_SUPABASE_KEY`
   - `TEST_WALLET_ADDRESS`
   - `TEST_WALLET_PRIVATE_KEY`

## Test Fixtures

Test fixtures are defined in `conftest.py`:
- `test_db`: Database connection
- `test_token`: POLYTALE token fixture
- `test_curator`: 0xdetweiler curator fixture
- `test_wallet`: Test wallet configuration
- `test_signal_id`: Unique signal ID generator
- `mock_engine_payload_*`: Mocked engine payloads for testing

## Test Helpers

Helper functions in `test_helpers.py`:
- `wait_for_condition()`: Polling helper for async operations
- `get_positions_by_token()`: Query positions by token
- `get_strand_by_id()`: Query strand by ID
- `get_coefficient()`: Query learning coefficient
- `get_global_rr_baseline()`: Query global R/R baseline
- `assert_allocation_splits()`: Assert allocation splits
- `assert_coefficient_bounds()`: Assert coefficient weight bounds

## Test Scenarios

### Scenario 1A: Uptrend Engine Testing
- Tests engine computation with real OHLC data
- No execution required

### Scenario 1B: Complete Learning Loop Flow Test
- Gold standard flow test
- Follows signal through entire pipeline
- Uses mocked engine payload for guaranteed execution

### Scenario 2: Cold Start
- Tests system without learned data
- Verifies fallback logic

### Scenario 4: EWMA Temporal Decay
- Tests EWMA with temporal decay
- Verifies recent trades weighted more heavily

### Scenario 9: PM/Executor Testing
- Comprehensive PM/Executor test suite
- 12 test cases covering all engine signal combinations

### Scenario 10: Majors Data Flow Test
- Critical dependency test
- Follows majors data through ingestion → rollup → SPIRAL consumption

### Scenario 11: SPIRAL Engine Testing
- Tests SPIRAL phase detection and A/E score computation
- Requires Scenario 10 to pass first

## Test Execution Order

1. **Layer 1: Component Tests** (run first)
   - Unit tests
   - Integration tests

2. **Layer 2: Flow Tests** (run after component tests)
   - Scenario 10 (Majors Data) - Run FIRST
   - Scenario 11 (SPIRAL) - Run AFTER Scenario 10
   - Scenario 1A (Engine) - Test engine with real data
   - Scenario 1B (Learning Loop) - Full pipeline test
   - Scenario 2 (Cold Start)
   - Scenario 4 (EWMA)
   - Scenario 9 (PM/Executor)

3. **Layer 3: Validation**
   - Performance tests
   - Data integrity checks
   - Regression tests

## Notes

- Flow tests require test environment setup
- Real execution uses small amounts ($5-10 per trade)
- Tests use real tokens and curators from fixtures
- Mocked engine payloads used for guaranteed execution testing
