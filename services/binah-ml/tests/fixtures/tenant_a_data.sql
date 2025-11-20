-- Test Fixtures for Tenant A
-- Tenant ID: aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa
-- Description: Complete test dataset for integration testing

-- Clean up existing test data for tenant A
DELETE FROM model_metadata WHERE model_id IN (SELECT id FROM ml_models WHERE tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
DELETE FROM predictions WHERE tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
DELETE FROM training_jobs WHERE tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
DELETE FROM ml_models WHERE tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';

-- Insert ML Models for Tenant A
INSERT INTO ml_models (id, tenant_id, model_type, model_name, model_version, mlflow_run_id, mlflow_model_uri, status, metrics, hyperparameters, created_at, updated_at, created_by) VALUES
-- Cost Forecasting Models
('a1111111-1111-1111-1111-111111111111', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cost_forecasting', 'Cost Forecast Model v1.0', '1.0', 'run_a_cost_v1_001', 's3://mlflow/artifacts/run_a_cost_v1_001/model', 'ready',
 '{"rmse": 15000.50, "mae": 12000.25, "r2": 0.92}',
 '{"n_estimators": 100, "max_depth": 6, "learning_rate": 0.1}',
 NOW() - INTERVAL '30 days', NOW() - INTERVAL '30 days', 'a0000000-0000-0000-0000-000000000001'),

('a1111111-1111-1111-1111-111111111112', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cost_forecasting', 'Cost Forecast Model v2.0', '2.0', 'run_a_cost_v2_001', 's3://mlflow/artifacts/run_a_cost_v2_001/model', 'ready',
 '{"rmse": 13500.75, "mae": 11000.50, "r2": 0.94}',
 '{"n_estimators": 150, "max_depth": 8, "learning_rate": 0.08}',
 NOW() - INTERVAL '15 days', NOW() - INTERVAL '15 days', 'a0000000-0000-0000-0000-000000000001'),

-- Risk Assessment Models
('a2222222-2222-2222-2222-222222222222', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'risk_assessment', 'Risk Model A v1.0', '1.0', 'run_a_risk_v1_001', 's3://mlflow/artifacts/run_a_risk_v1_001/model', 'ready',
 '{"accuracy": 0.87, "auc_roc": 0.91}',
 '{"n_estimators": 100, "max_depth": 10}',
 NOW() - INTERVAL '25 days', NOW() - INTERVAL '25 days', 'a0000000-0000-0000-0000-000000000002'),

-- ROI Prediction Models
('a3333333-3333-3333-3333-333333333333', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'roi_prediction', 'ROI Predictor v1.0', '1.0', 'run_a_roi_v1_001', 's3://mlflow/artifacts/run_a_roi_v1_001/model', 'ready',
 '{"rmse": 2.5, "mae": 1.8, "r2": 0.88}',
 '{"n_estimators": 120, "max_depth": 7, "learning_rate": 0.1}',
 NOW() - INTERVAL '20 days', NOW() - INTERVAL '20 days', 'a0000000-0000-0000-0000-000000000001'),

-- Anomaly Detection Models
('a4444444-4444-4444-4444-444444444444', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'anomaly_detection', 'Anomaly Detector v1.0', '1.0', 'run_a_anomaly_v1_001', 's3://mlflow/artifacts/run_a_anomaly_v1_001/model', 'ready',
 '{"anomaly_rate": 0.048, "anomalies_detected": 48}',
 '{"n_estimators": 100, "contamination": 0.05}',
 NOW() - INTERVAL '10 days', NOW() - INTERVAL '10 days', 'a0000000-0000-0000-0000-000000000003'),

-- Model in training
('a5555555-5555-5555-5555-555555555555', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cost_forecasting', 'Cost Forecast Model v3.0', '3.0', 'run_a_cost_v3_001', NULL, 'training',
 NULL,
 '{"n_estimators": 200, "max_depth": 10, "learning_rate": 0.05}',
 NOW() - INTERVAL '1 hour', NOW() - INTERVAL '1 hour', 'a0000000-0000-0000-0000-000000000001');

-- Insert Training Jobs for Tenant A
INSERT INTO training_jobs (id, tenant_id, model_type, model_id, status, mlflow_run_id, training_data_query, hyperparameters, validation_split, started_at, completed_at, error_message, metrics, created_at, created_by) VALUES
-- Completed training jobs
('a1111111-1111-1111-1111-111111111101', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cost_forecasting', 'a1111111-1111-1111-1111-111111111111', 'completed', 'run_a_cost_v1_001',
 'SELECT * FROM training_data WHERE tenant_id = ''aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'' AND model_type = ''cost_forecasting''',
 '{"n_estimators": 100, "max_depth": 6, "learning_rate": 0.1}', 0.20,
 NOW() - INTERVAL '30 days 2 hours', NOW() - INTERVAL '30 days', NULL,
 '{"rmse": 15000.50, "mae": 12000.25, "r2": 0.92}',
 NOW() - INTERVAL '30 days 2 hours', 'a0000000-0000-0000-0000-000000000001'),

('a1111111-1111-1111-1111-111111111102', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cost_forecasting', 'a1111111-1111-1111-1111-111111111112', 'completed', 'run_a_cost_v2_001',
 'SELECT * FROM training_data WHERE tenant_id = ''aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'' AND model_type = ''cost_forecasting''',
 '{"n_estimators": 150, "max_depth": 8, "learning_rate": 0.08}', 0.20,
 NOW() - INTERVAL '15 days 2 hours', NOW() - INTERVAL '15 days', NULL,
 '{"rmse": 13500.75, "mae": 11000.50, "r2": 0.94}',
 NOW() - INTERVAL '15 days 2 hours', 'a0000000-0000-0000-0000-000000000001'),

('a2222222-2222-2222-2222-222222222201', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'risk_assessment', 'a2222222-2222-2222-2222-222222222222', 'completed', 'run_a_risk_v1_001',
 'SELECT * FROM training_data WHERE tenant_id = ''aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'' AND model_type = ''risk_assessment''',
 '{"n_estimators": 100, "max_depth": 10}', 0.20,
 NOW() - INTERVAL '25 days 1 hour', NOW() - INTERVAL '25 days', NULL,
 '{"accuracy": 0.87, "auc_roc": 0.91}',
 NOW() - INTERVAL '25 days 1 hour', 'a0000000-0000-0000-0000-000000000002'),

-- Running training job
('a5555555-5555-5555-5555-555555555501', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'cost_forecasting', 'a5555555-5555-5555-5555-555555555555', 'running', 'run_a_cost_v3_001',
 'SELECT * FROM training_data WHERE tenant_id = ''aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'' AND model_type = ''cost_forecasting''',
 '{"n_estimators": 200, "max_depth": 10, "learning_rate": 0.05}', 0.20,
 NOW() - INTERVAL '1 hour', NULL, NULL, NULL,
 NOW() - INTERVAL '1 hour', 'a0000000-0000-0000-0000-000000000001'),

-- Failed training job
('a6666666-6666-6666-6666-666666666601', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'roi_prediction', NULL, 'failed', 'run_a_roi_v2_001',
 'SELECT * FROM training_data WHERE tenant_id = ''aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa'' AND model_type = ''roi_prediction''',
 '{"n_estimators": 50, "max_depth": 3}', 0.20,
 NOW() - INTERVAL '5 days 1 hour', NOW() - INTERVAL '5 days 30 minutes',
 'Insufficient training data: only 100 samples available, minimum 500 required', NULL,
 NOW() - INTERVAL '5 days 1 hour', 'a0000000-0000-0000-0000-000000000001');

-- Insert Predictions for Tenant A
INSERT INTO predictions (id, tenant_id, model_id, model_type, model_version, input_features, prediction_result, confidence, created_at, created_by) VALUES
-- Cost forecasting predictions
('a1111111-1111-1111-1111-111111111201', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a1111111-1111-1111-1111-111111111112', 'cost_forecasting', '2.0',
 '{"project_size_sqft": 5000, "num_units": 50, "location_tier": 2, "property_type": 1, "year": 2024}',
 '{"predicted_cost": 1250000.75, "cost_per_sqft": 250.00, "cost_breakdown": {"materials": 750000, "labor": 400000, "overhead": 100000}}',
 0.94, NOW() - INTERVAL '5 days', 'a0000000-0000-0000-0000-000000000001'),

('a1111111-1111-1111-1111-111111111202', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a1111111-1111-1111-1111-111111111112', 'cost_forecasting', '2.0',
 '{"project_size_sqft": 8000, "num_units": 80, "location_tier": 1, "property_type": 2, "year": 2024}',
 '{"predicted_cost": 2150000.50, "cost_per_sqft": 268.75, "cost_breakdown": {"materials": 1290000, "labor": 680000, "overhead": 180000}}',
 0.92, NOW() - INTERVAL '4 days', 'a0000000-0000-0000-0000-000000000002'),

-- Risk assessment predictions
('a2222222-2222-2222-2222-222222222201', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a2222222-2222-2222-2222-222222222222', 'risk_assessment', '1.0',
 '{"leverage_ratio": 0.75, "occupancy_rate": 0.92, "market_volatility": 0.45, "property_age": 10, "location_risk_score": 3.5}',
 '{"risk_level": "medium", "risk_score": 0.55, "recommendation": "Proceed with standard due diligence"}',
 0.87, NOW() - INTERVAL '3 days', 'a0000000-0000-0000-0000-000000000001'),

('a2222222-2222-2222-2222-222222222202', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a2222222-2222-2222-2222-222222222222', 'risk_assessment', '1.0',
 '{"leverage_ratio": 0.85, "occupancy_rate": 0.78, "market_volatility": 0.72, "property_age": 25, "location_risk_score": 6.8}',
 '{"risk_level": "high", "risk_score": 0.82, "recommendation": "Enhanced risk mitigation required"}',
 0.91, NOW() - INTERVAL '2 days', 'a0000000-0000-0000-0000-000000000003'),

-- ROI predictions
('a3333333-3333-3333-3333-333333333301', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a3333333-3333-3333-3333-333333333333', 'roi_prediction', '1.0',
 '{"purchase_price": 2000000, "annual_revenue": 180000, "operating_expenses": 60000, "property_type": 1, "market_growth_rate": 0.08}',
 '{"predicted_roi": 6.8, "projected_noi": 120000, "payback_period_years": 14.7}',
 0.88, NOW() - INTERVAL '1 day', 'a0000000-0000-0000-0000-000000000002'),

-- Recent predictions (last 6 hours)
('a1111111-1111-1111-1111-111111111203', 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa', 'a1111111-1111-1111-1111-111111111112', 'cost_forecasting', '2.0',
 '{"project_size_sqft": 3500, "num_units": 35, "location_tier": 3, "property_type": 1, "year": 2024}',
 '{"predicted_cost": 825000.25, "cost_per_sqft": 235.71, "cost_breakdown": {"materials": 495000, "labor": 280000, "overhead": 50000}}',
 0.93, NOW() - INTERVAL '2 hours', 'a0000000-0000-0000-0000-000000000001');

-- Insert Model Metadata for Tenant A
INSERT INTO model_metadata (id, model_id, key, value, created_at) VALUES
('a1111111-1111-1111-1111-111111111301', 'a1111111-1111-1111-1111-111111111112', 'training_samples', '15000', NOW() - INTERVAL '15 days'),
('a1111111-1111-1111-1111-111111111302', 'a1111111-1111-1111-1111-111111111112', 'training_duration_minutes', '45', NOW() - INTERVAL '15 days'),
('a1111111-1111-1111-1111-111111111303', 'a1111111-1111-1111-1111-111111111112', 'feature_importance', '{"project_size_sqft": 0.45, "num_units": 0.30, "location_tier": 0.15, "property_type": 0.07, "year": 0.03}', NOW() - INTERVAL '15 days'),
('a1111111-1111-1111-1111-111111111304', 'a1111111-1111-1111-1111-111111111112', 'data_source', 'PostgreSQL:training_data', NOW() - INTERVAL '15 days'),

('a2222222-2222-2222-2222-222222222301', 'a2222222-2222-2222-2222-222222222222', 'training_samples', '8000', NOW() - INTERVAL '25 days'),
('a2222222-2222-2222-2222-222222222302', 'a2222222-2222-2222-2222-222222222222', 'training_duration_minutes', '32', NOW() - INTERVAL '25 days'),
('a2222222-2222-2222-2222-222222222303', 'a2222222-2222-2222-2222-222222222222', 'feature_importance', '{"leverage_ratio": 0.35, "market_volatility": 0.28, "location_risk_score": 0.20, "occupancy_rate": 0.12, "property_age": 0.05}', NOW() - INTERVAL '25 days'),

('a3333333-3333-3333-3333-333333333301', 'a3333333-3333-3333-3333-333333333333', 'training_samples', '12000', NOW() - INTERVAL '20 days'),
('a3333333-3333-3333-3333-333333333302', 'a3333333-3333-3333-3333-333333333333', 'training_duration_minutes', '38', NOW() - INTERVAL '20 days');

-- Verify data insertion
SELECT 'Tenant A: Inserted ' || COUNT(*) || ' models' FROM ml_models WHERE tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
SELECT 'Tenant A: Inserted ' || COUNT(*) || ' training jobs' FROM training_jobs WHERE tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
SELECT 'Tenant A: Inserted ' || COUNT(*) || ' predictions' FROM predictions WHERE tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa';
SELECT 'Tenant A: Inserted ' || COUNT(*) || ' metadata entries' FROM model_metadata WHERE model_id IN (SELECT id FROM ml_models WHERE tenant_id = 'aaaaaaaa-aaaa-aaaa-aaaa-aaaaaaaaaaaa');
