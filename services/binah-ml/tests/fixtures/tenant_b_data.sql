-- Test Fixtures for Tenant B
-- Tenant ID: bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb
-- Description: Complete test dataset for integration testing

-- Clean up existing test data for tenant B
DELETE FROM model_metadata WHERE model_id IN (SELECT id FROM ml_models WHERE tenant_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb');
DELETE FROM predictions WHERE tenant_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';
DELETE FROM training_jobs WHERE tenant_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';
DELETE FROM ml_models WHERE tenant_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';

-- Insert ML Models for Tenant B
INSERT INTO ml_models (id, tenant_id, model_type, model_name, model_version, mlflow_run_id, mlflow_model_uri, status, metrics, hyperparameters, created_at, updated_at, created_by) VALUES
-- Cost Forecasting Models
('b1111111-1111-1111-1111-111111111111', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'cost_forecasting', 'Enterprise Cost Model v1.0', '1.0', 'run_b_cost_v1_001', 's3://mlflow/artifacts/run_b_cost_v1_001/model', 'ready',
 '{"rmse": 18000.25, "mae": 14500.75, "r2": 0.89}',
 '{"n_estimators": 80, "max_depth": 5, "learning_rate": 0.12}',
 NOW() - INTERVAL '28 days', NOW() - INTERVAL '28 days', 'b0000000-0000-0000-0000-000000000001'),

('b1111111-1111-1111-1111-111111111112', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'cost_forecasting', 'Enterprise Cost Model v1.1', '1.1', 'run_b_cost_v1_1_001', 's3://mlflow/artifacts/run_b_cost_v1_1_001/model', 'ready',
 '{"rmse": 16500.50, "mae": 13200.30, "r2": 0.91}',
 '{"n_estimators": 100, "max_depth": 6, "learning_rate": 0.1}',
 NOW() - INTERVAL '12 days', NOW() - INTERVAL '12 days', 'b0000000-0000-0000-0000-000000000001'),

-- Risk Assessment Models
('b2222222-2222-2222-2222-222222222222', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'risk_assessment', 'Commercial Risk Analyzer v1.0', '1.0', 'run_b_risk_v1_001', 's3://mlflow/artifacts/run_b_risk_v1_001/model', 'ready',
 '{"accuracy": 0.85, "auc_roc": 0.89}',
 '{"n_estimators": 120, "max_depth": 12}',
 NOW() - INTERVAL '22 days', NOW() - INTERVAL '22 days', 'b0000000-0000-0000-0000-000000000002'),

-- ROI Prediction Models
('b3333333-3333-3333-3333-333333333333', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'roi_prediction', 'ROI Calculator Pro v1.0', '1.0', 'run_b_roi_v1_001', 's3://mlflow/artifacts/run_b_roi_v1_001/model', 'ready',
 '{"rmse": 3.2, "mae": 2.4, "r2": 0.85}',
 '{"n_estimators": 100, "max_depth": 6, "learning_rate": 0.12}',
 NOW() - INTERVAL '18 days', NOW() - INTERVAL '18 days', 'b0000000-0000-0000-0000-000000000001'),

-- Anomaly Detection Models
('b4444444-4444-4444-4444-444444444444', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'anomaly_detection', 'Outlier Detection System v1.0', '1.0', 'run_b_anomaly_v1_001', 's3://mlflow/artifacts/run_b_anomaly_v1_001/model', 'ready',
 '{"anomaly_rate": 0.062, "anomalies_detected": 62}',
 '{"n_estimators": 150, "contamination": 0.06}',
 NOW() - INTERVAL '8 days', NOW() - INTERVAL '8 days', 'b0000000-0000-0000-0000-000000000003'),

-- Deprecated model
('b5555555-5555-5555-5555-555555555555', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'cost_forecasting', 'Legacy Cost Model v0.9', '0.9', 'run_b_cost_v0_9_001', 's3://mlflow/artifacts/run_b_cost_v0_9_001/model', 'deprecated',
 '{"rmse": 22000.00, "mae": 18000.00, "r2": 0.78}',
 '{"n_estimators": 50, "max_depth": 4, "learning_rate": 0.15}',
 NOW() - INTERVAL '60 days', NOW() - INTERVAL '30 days', 'b0000000-0000-0000-0000-000000000001');

-- Insert Training Jobs for Tenant B
INSERT INTO training_jobs (id, tenant_id, model_type, model_id, status, mlflow_run_id, training_data_query, hyperparameters, validation_split, started_at, completed_at, error_message, metrics, created_at, created_by) VALUES
-- Completed training jobs
('b1111111-1111-1111-1111-111111111101', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'cost_forecasting', 'b1111111-1111-1111-1111-111111111111', 'completed', 'run_b_cost_v1_001',
 'SELECT * FROM training_data WHERE tenant_id = ''bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'' AND model_type = ''cost_forecasting''',
 '{"n_estimators": 80, "max_depth": 5, "learning_rate": 0.12}', 0.20,
 NOW() - INTERVAL '28 days 3 hours', NOW() - INTERVAL '28 days', NULL,
 '{"rmse": 18000.25, "mae": 14500.75, "r2": 0.89}',
 NOW() - INTERVAL '28 days 3 hours', 'b0000000-0000-0000-0000-000000000001'),

('b1111111-1111-1111-1111-111111111102', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'cost_forecasting', 'b1111111-1111-1111-1111-111111111112', 'completed', 'run_b_cost_v1_1_001',
 'SELECT * FROM training_data WHERE tenant_id = ''bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'' AND model_type = ''cost_forecasting''',
 '{"n_estimators": 100, "max_depth": 6, "learning_rate": 0.1}', 0.20,
 NOW() - INTERVAL '12 days 2 hours', NOW() - INTERVAL '12 days', NULL,
 '{"rmse": 16500.50, "mae": 13200.30, "r2": 0.91}',
 NOW() - INTERVAL '12 days 2 hours', 'b0000000-0000-0000-0000-000000000001'),

('b2222222-2222-2222-2222-222222222201', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'risk_assessment', 'b2222222-2222-2222-2222-222222222222', 'completed', 'run_b_risk_v1_001',
 'SELECT * FROM training_data WHERE tenant_id = ''bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'' AND model_type = ''risk_assessment''',
 '{"n_estimators": 120, "max_depth": 12}', 0.20,
 NOW() - INTERVAL '22 days 2 hours', NOW() - INTERVAL '22 days', NULL,
 '{"accuracy": 0.85, "auc_roc": 0.89}',
 NOW() - INTERVAL '22 days 2 hours', 'b0000000-0000-0000-0000-000000000002'),

-- Queued training job
('b6666666-6666-6666-6666-666666666601', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'anomaly_detection', NULL, 'queued', 'run_b_anomaly_v2_001',
 'SELECT * FROM training_data WHERE tenant_id = ''bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'' AND model_type = ''anomaly_detection''',
 '{"n_estimators": 200, "contamination": 0.04}', 0.20,
 NULL, NULL, NULL, NULL,
 NOW() - INTERVAL '30 minutes', 'b0000000-0000-0000-0000-000000000003'),

-- Cancelled training job
('b7777777-7777-7777-7777-777777777701', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'roi_prediction', NULL, 'cancelled', 'run_b_roi_v2_001',
 'SELECT * FROM training_data WHERE tenant_id = ''bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb'' AND model_type = ''roi_prediction''',
 '{"n_estimators": 80, "max_depth": 5}', 0.20,
 NOW() - INTERVAL '7 days 1 hour', NOW() - INTERVAL '7 days 30 minutes',
 'Training cancelled by user', NULL,
 NOW() - INTERVAL '7 days 1 hour', 'b0000000-0000-0000-0000-000000000001');

-- Insert Predictions for Tenant B
INSERT INTO predictions (id, tenant_id, model_id, model_type, model_version, input_features, prediction_result, confidence, created_at, created_by) VALUES
-- Cost forecasting predictions
('b1111111-1111-1111-1111-111111111201', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'b1111111-1111-1111-1111-111111111112', 'cost_forecasting', '1.1',
 '{"project_size_sqft": 12000, "num_units": 120, "location_tier": 1, "property_type": 3, "year": 2024}',
 '{"predicted_cost": 3250000.50, "cost_per_sqft": 270.83, "cost_breakdown": {"materials": 1950000, "labor": 1040000, "overhead": 260000}}',
 0.91, NOW() - INTERVAL '6 days', 'b0000000-0000-0000-0000-000000000001'),

('b1111111-1111-1111-1111-111111111202', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'b1111111-1111-1111-1111-111111111112', 'cost_forecasting', '1.1',
 '{"project_size_sqft": 6500, "num_units": 65, "location_tier": 2, "property_type": 2, "year": 2024}',
 '{"predicted_cost": 1720000.75, "cost_per_sqft": 264.62, "cost_breakdown": {"materials": 1032000, "labor": 550000, "overhead": 138000}}',
 0.89, NOW() - INTERVAL '5 days', 'b0000000-0000-0000-0000-000000000002'),

-- Risk assessment predictions
('b2222222-2222-2222-2222-222222222201', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'b2222222-2222-2222-2222-222222222222', 'risk_assessment', '1.0',
 '{"leverage_ratio": 0.68, "occupancy_rate": 0.95, "market_volatility": 0.35, "property_age": 5, "location_risk_score": 2.8}',
 '{"risk_level": "low", "risk_score": 0.32, "recommendation": "Good investment opportunity"}',
 0.85, NOW() - INTERVAL '4 days', 'b0000000-0000-0000-0000-000000000001'),

('b2222222-2222-2222-2222-222222222202', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'b2222222-2222-2222-2222-222222222222', 'risk_assessment', '1.0',
 '{"leverage_ratio": 0.88, "occupancy_rate": 0.72, "market_volatility": 0.78, "property_age": 35, "location_risk_score": 7.5}',
 '{"risk_level": "high", "risk_score": 0.86, "recommendation": "Significant risk mitigation required"}',
 0.89, NOW() - INTERVAL '3 days', 'b0000000-0000-0000-0000-000000000003'),

-- ROI predictions
('b3333333-3333-3333-3333-333333333301', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'b3333333-3333-3333-3333-333333333333', 'roi_prediction', '1.0',
 '{"purchase_price": 3500000, "annual_revenue": 280000, "operating_expenses": 95000, "property_type": 2, "market_growth_rate": 0.06}',
 '{"predicted_roi": 5.9, "projected_noi": 185000, "payback_period_years": 16.9}',
 0.85, NOW() - INTERVAL '2 days', 'b0000000-0000-0000-0000-000000000002'),

-- Recent predictions (last 12 hours)
('b1111111-1111-1111-1111-111111111203', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'b1111111-1111-1111-1111-111111111112', 'cost_forecasting', '1.1',
 '{"project_size_sqft": 4200, "num_units": 42, "location_tier": 2, "property_type": 1, "year": 2024}',
 '{"predicted_cost": 1050000.00, "cost_per_sqft": 250.00, "cost_breakdown": {"materials": 630000, "labor": 336000, "overhead": 84000}}',
 0.90, NOW() - INTERVAL '4 hours', 'b0000000-0000-0000-0000-000000000001'),

('b2222222-2222-2222-2222-222222222203', 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb', 'b2222222-2222-2222-2222-222222222222', 'risk_assessment', '1.0',
 '{"leverage_ratio": 0.72, "occupancy_rate": 0.88, "market_volatility": 0.52, "property_age": 15, "location_risk_score": 4.2}',
 '{"risk_level": "medium", "risk_score": 0.58, "recommendation": "Standard due diligence recommended"}',
 0.87, NOW() - INTERVAL '1 hour', 'b0000000-0000-0000-0000-000000000002');

-- Insert Model Metadata for Tenant B
INSERT INTO model_metadata (id, model_id, key, value, created_at) VALUES
('b1111111-1111-1111-1111-111111111301', 'b1111111-1111-1111-1111-111111111112', 'training_samples', '18000', NOW() - INTERVAL '12 days'),
('b1111111-1111-1111-1111-111111111302', 'b1111111-1111-1111-1111-111111111112', 'training_duration_minutes', '52', NOW() - INTERVAL '12 days'),
('b1111111-1111-1111-1111-111111111303', 'b1111111-1111-1111-1111-111111111112', 'feature_importance', '{"project_size_sqft": 0.42, "num_units": 0.32, "location_tier": 0.16, "property_type": 0.08, "year": 0.02}', NOW() - INTERVAL '12 days'),
('b1111111-1111-1111-1111-111111111304', 'b1111111-1111-1111-1111-111111111112', 'data_source', 'PostgreSQL:training_data', NOW() - INTERVAL '12 days'),
('b1111111-1111-1111-1111-111111111305', 'b1111111-1111-1111-1111-111111111112', 'model_size_mb', '12.5', NOW() - INTERVAL '12 days'),

('b2222222-2222-2222-2222-222222222301', 'b2222222-2222-2222-2222-222222222222', 'training_samples', '10000', NOW() - INTERVAL '22 days'),
('b2222222-2222-2222-2222-222222222302', 'b2222222-2222-2222-2222-222222222222', 'training_duration_minutes', '41', NOW() - INTERVAL '22 days'),
('b2222222-2222-2222-2222-222222222303', 'b2222222-2222-2222-2222-222222222222', 'feature_importance', '{"leverage_ratio": 0.38, "market_volatility": 0.26, "location_risk_score": 0.22, "occupancy_rate": 0.10, "property_age": 0.04}', NOW() - INTERVAL '22 days'),

('b3333333-3333-3333-3333-333333333301', 'b3333333-3333-3333-3333-333333333333', 'training_samples', '14000', NOW() - INTERVAL '18 days'),
('b3333333-3333-3333-3333-333333333302', 'b3333333-3333-3333-3333-333333333333', 'training_duration_minutes', '44', NOW() - INTERVAL '18 days'),
('b3333333-3333-3333-3333-333333333303', 'b3333333-3333-3333-3333-333333333333', 'model_size_mb', '8.2', NOW() - INTERVAL '18 days');

-- Verify data insertion
SELECT 'Tenant B: Inserted ' || COUNT(*) || ' models' FROM ml_models WHERE tenant_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';
SELECT 'Tenant B: Inserted ' || COUNT(*) || ' training jobs' FROM training_jobs WHERE tenant_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';
SELECT 'Tenant B: Inserted ' || COUNT(*) || ' predictions' FROM predictions WHERE tenant_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb';
SELECT 'Tenant B: Inserted ' || COUNT(*) || ' metadata entries' FROM model_metadata WHERE model_id IN (SELECT id FROM ml_models WHERE tenant_id = 'bbbbbbbb-bbbb-bbbb-bbbb-bbbbbbbbbbbb');
