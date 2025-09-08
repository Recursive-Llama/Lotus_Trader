-- Database Views for Resonance-Enhanced Scoring
-- These views implement the mathematical resonance equations and enhanced scoring

-- View for resonance-enhanced scores
CREATE OR REPLACE VIEW v_resonance_enhanced_scores AS
SELECT 
    s.id,
    s.sig_sigma,
    s.sig_confidence,
    s.outcome_score,
    s.phi,
    s.rho,
    s.telemetry->>'surprise' as surprise,
    s.telemetry->>'sr' as success_rate,
    s.telemetry->>'cr' as confirmation_rate,
    s.telemetry->>'xr' as contradiction_rate,
    
    -- Current enhanced scoring (already built)
    (s.sig_sigma * 0.4 + s.sig_confidence * 0.3 + s.outcome_score * 0.3) as current_score,
    
    -- Resonance score from MotifCard
    (s.phi * s.rho * COALESCE((s.telemetry->>'surprise')::float, 0.0)) as resonance_score,
    
    -- Enhanced final score with resonance boost
    (s.sig_sigma * 0.4 + s.sig_confidence * 0.3 + s.outcome_score * 0.3) * 
    (1 + (s.phi * s.rho * COALESCE((s.telemetry->>'surprise')::float, 0.0)) * 0.2) as final_score,
    
    -- Resonance field strength
    (s.phi * s.rho) as field_strength,
    
    -- Resonance quality metrics
    CASE 
        WHEN s.phi > 0.8 AND s.rho > 1.2 THEN 'high_resonance'
        WHEN s.phi > 0.5 AND s.rho > 1.0 THEN 'medium_resonance'
        WHEN s.phi > 0.2 AND s.rho > 0.8 THEN 'low_resonance'
        ELSE 'no_resonance'
    END as resonance_quality,
    
    s.created_at,
    s.updated_at
FROM AD_strands s
WHERE s.kind = 'motif'
    AND s.created_at >= NOW() - INTERVAL '24 hours'
ORDER BY final_score DESC;

-- View for resonance rates calculation
CREATE OR REPLACE VIEW v_resonance_rates AS
SELECT 
    motif_id,
    motif_name,
    motif_family,
    
    -- Success rate calculation
    AVG(CASE WHEN outcome_score > 0 THEN 1.0 ELSE 0.0 END) as success_rate,
    
    -- Confirmation rate calculation
    AVG(CASE WHEN sig_confidence > 0.7 THEN 1.0 ELSE 0.0 END) as confirmation_rate,
    
    -- Contradiction rate calculation
    AVG(CASE WHEN outcome_score < -0.5 THEN 1.0 ELSE 0.0 END) as contradiction_rate,
    
    -- Surprise rate calculation (based on rarity)
    CASE 
        WHEN COUNT(*) = 1 THEN 1.0
        WHEN COUNT(*) < 5 THEN 0.8
        WHEN COUNT(*) < 20 THEN 0.5
        ELSE 0.2
    END as surprise_rate,
    
    -- Total occurrences
    COUNT(*) as total_occurrences,
    
    -- Average metrics
    AVG(sig_sigma) as avg_sigma,
    AVG(sig_confidence) as avg_confidence,
    AVG(outcome_score) as avg_outcome,
    
    -- Time range
    MIN(created_at) as first_occurrence,
    MAX(created_at) as last_occurrence
    
FROM AD_strands
WHERE kind = 'motif'
    AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY motif_id, motif_name, motif_family
HAVING COUNT(*) >= 5  -- Minimum samples for reliable rates
ORDER BY success_rate DESC, total_occurrences DESC;

-- View for resonance field analysis
CREATE OR REPLACE VIEW v_resonance_field_analysis AS
SELECT 
    motif_family,
    regime,
    session_bucket,
    
    -- Family-level resonance metrics
    AVG(phi) as avg_phi,
    AVG(rho) as avg_rho,
    AVG(phi * rho) as avg_field_strength,
    
    -- Family-level performance metrics
    AVG(COALESCE((telemetry->>'sr')::float, 0.0)) as avg_success_rate,
    AVG(COALESCE((telemetry->>'cr')::float, 0.0)) as avg_confirmation_rate,
    AVG(COALESCE((telemetry->>'xr')::float, 0.0)) as avg_contradiction_rate,
    AVG(COALESCE((telemetry->>'surprise')::float, 0.0)) as avg_surprise,
    
    -- Count metrics
    COUNT(*) as motif_count,
    COUNT(DISTINCT motif_id) as unique_motifs,
    
    -- Resonance quality distribution
    COUNT(CASE WHEN phi > 0.8 AND rho > 1.2 THEN 1 END) as high_resonance_count,
    COUNT(CASE WHEN phi > 0.5 AND rho > 1.0 THEN 1 END) as medium_resonance_count,
    COUNT(CASE WHEN phi > 0.2 AND rho > 0.8 THEN 1 END) as low_resonance_count,
    
    -- Time metrics
    MIN(created_at) as first_occurrence,
    MAX(created_at) as last_occurrence,
    MAX(phi_updated_at) as last_phi_update,
    MAX(rho_updated_at) as last_rho_update
    
FROM AD_strands
WHERE kind = 'motif'
    AND created_at >= NOW() - INTERVAL '24 hours'
GROUP BY motif_family, regime, session_bucket
ORDER BY avg_field_strength DESC;

-- View for resonance-enhanced experiment queue
CREATE OR REPLACE VIEW v_resonance_experiment_queue AS
SELECT 
    eq.candidate_id,
    eq.motif_id,
    eq.family,
    eq.resonance_score,
    eq.cap_rank,
    eq.created_at,
    
    -- Hypothesis details
    h.hypothesis_text,
    h.experiment_shape,
    h.success_metric,
    h.min_samples,
    h.ttl_hours,
    
    -- Motif details
    m.motif_name,
    m.motif_family,
    m.phi,
    m.rho,
    m.telemetry,
    
    -- Enhanced scoring
    (m.phi * m.rho * COALESCE((m.telemetry->>'surprise')::float, 0.0)) as calculated_resonance_score,
    
    -- Priority classification
    CASE 
        WHEN eq.resonance_score > 0.8 THEN 'high_priority'
        WHEN eq.resonance_score > 0.5 THEN 'medium_priority'
        WHEN eq.resonance_score > 0.2 THEN 'low_priority'
        ELSE 'very_low_priority'
    END as priority_level,
    
    -- Family balance
    ROW_NUMBER() OVER (PARTITION BY eq.family ORDER BY eq.resonance_score DESC) as family_rank
    
FROM experiment_queue eq
LEFT JOIN AD_strands h ON eq.candidate_id = h.hypothesis_id
LEFT JOIN AD_strands m ON eq.motif_id = m.id
ORDER BY eq.resonance_score DESC, eq.cap_rank;

-- View for resonance system health
CREATE OR REPLACE VIEW v_resonance_system_health AS
SELECT 
    -- Global resonance state
    rs.theta as global_theta,
    rs.updated_at as theta_updated_at,
    rs.window,
    rs.delta,
    rs.alpha,
    rs.gamma,
    rs.rho_min,
    rs.rho_max,
    
    -- System metrics
    (SELECT COUNT(*) FROM AD_strands WHERE kind = 'motif' AND phi > 0.1) as active_motifs,
    (SELECT COUNT(*) FROM AD_strands WHERE kind = 'motif' AND phi > 0.8) as high_resonance_motifs,
    (SELECT COUNT(*) FROM experiment_queue) as queued_experiments,
    (SELECT COUNT(*) FROM AD_strands WHERE kind = 'resonance_event' AND created_at > NOW() - INTERVAL '1 hour') as recent_events,
    
    -- Performance metrics
    (SELECT AVG(phi) FROM AD_strands WHERE kind = 'motif' AND phi > 0.1) as avg_phi,
    (SELECT AVG(rho) FROM AD_strands WHERE kind = 'motif' AND rho > 0.1) as avg_rho,
    (SELECT AVG(phi * rho) FROM AD_strands WHERE kind = 'motif' AND phi > 0.1) as avg_field_strength,
    
    -- Health indicators
    CASE 
        WHEN rs.theta > 0.5 AND (SELECT COUNT(*) FROM AD_strands WHERE kind = 'motif' AND phi > 0.1) > 10 THEN 'healthy'
        WHEN rs.theta > 0.2 AND (SELECT COUNT(*) FROM AD_strands WHERE kind = 'motif' AND phi > 0.1) > 5 THEN 'degraded'
        ELSE 'unhealthy'
    END as system_health,
    
    -- Last update times
    (SELECT MAX(phi_updated_at) FROM AD_strands WHERE kind = 'motif') as last_phi_update,
    (SELECT MAX(rho_updated_at) FROM AD_strands WHERE kind = 'motif') as last_rho_update,
    (SELECT MAX(created_at) FROM experiment_queue) as last_queue_update
    
FROM CIL_Resonance_State rs
ORDER BY rs.updated_at DESC
LIMIT 1;

-- View for resonance learning progress
CREATE OR REPLACE VIEW v_resonance_learning_progress AS
SELECT 
    DATE_TRUNC('hour', created_at) as hour_bucket,
    motif_family,
    
    -- Learning metrics
    COUNT(*) as motif_occurrences,
    AVG(phi) as avg_phi,
    AVG(rho) as avg_rho,
    AVG(phi * rho) as avg_field_strength,
    
    -- Performance metrics
    AVG(COALESCE((telemetry->>'sr')::float, 0.0)) as avg_success_rate,
    AVG(COALESCE((telemetry->>'cr')::float, 0.0)) as avg_confirmation_rate,
    AVG(COALESCE((telemetry->>'xr')::float, 0.0)) as avg_contradiction_rate,
    AVG(COALESCE((telemetry->>'surprise')::float, 0.0)) as avg_surprise,
    
    -- Learning indicators
    CASE 
        WHEN AVG(phi) > LAG(AVG(phi)) OVER (PARTITION BY motif_family ORDER BY DATE_TRUNC('hour', created_at)) THEN 'improving'
        WHEN AVG(phi) < LAG(AVG(phi)) OVER (PARTITION BY motif_family ORDER BY DATE_TRUNC('hour', created_at)) THEN 'declining'
        ELSE 'stable'
    END as learning_trend,
    
    -- Resonance quality
    COUNT(CASE WHEN phi > 0.8 AND rho > 1.2 THEN 1 END) as high_resonance_count,
    COUNT(CASE WHEN phi > 0.5 AND rho > 1.0 THEN 1 END) as medium_resonance_count,
    COUNT(CASE WHEN phi > 0.2 AND rho > 0.8 THEN 1 END) as low_resonance_count
    
FROM AD_strands
WHERE kind = 'motif'
    AND created_at >= NOW() - INTERVAL '7 days'
GROUP BY DATE_TRUNC('hour', created_at), motif_family
ORDER BY hour_bucket DESC, avg_field_strength DESC;

-- Function to get resonance-enhanced score for a specific strand
CREATE OR REPLACE FUNCTION get_resonance_enhanced_score(strand_id TEXT)
RETURNS TABLE(
    strand_id TEXT,
    current_score FLOAT,
    resonance_score FLOAT,
    final_score FLOAT,
    resonance_quality TEXT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        s.id::TEXT,
        (s.sig_sigma * 0.4 + s.sig_confidence * 0.3 + s.outcome_score * 0.3)::FLOAT as current_score,
        (s.phi * s.rho * COALESCE((s.telemetry->>'surprise')::float, 0.0))::FLOAT as resonance_score,
        ((s.sig_sigma * 0.4 + s.sig_confidence * 0.3 + s.outcome_score * 0.3) * 
         (1 + (s.phi * s.rho * COALESCE((s.telemetry->>'surprise')::float, 0.0)) * 0.2))::FLOAT as final_score,
        CASE 
            WHEN s.phi > 0.8 AND s.rho > 1.2 THEN 'high_resonance'
            WHEN s.phi > 0.5 AND s.rho > 1.0 THEN 'medium_resonance'
            WHEN s.phi > 0.2 AND s.rho > 0.8 THEN 'low_resonance'
            ELSE 'no_resonance'
        END::TEXT as resonance_quality
    FROM AD_strands s
    WHERE s.id = strand_id;
END;
$$ LANGUAGE plpgsql;

-- Function to update resonance state for a motif
CREATE OR REPLACE FUNCTION update_motif_resonance(
    p_motif_id TEXT,
    p_phi FLOAT,
    p_rho FLOAT
) RETURNS VOID AS $$
BEGIN
    UPDATE AD_strands 
    SET 
        phi = p_phi,
        rho = p_rho,
        phi_updated_at = NOW(),
        rho_updated_at = NOW()
    WHERE id = p_motif_id;
END;
$$ LANGUAGE plpgsql;

-- Function to calculate resonance score for experiment prioritization
CREATE OR REPLACE FUNCTION calculate_experiment_resonance_score(
    p_hypothesis_id TEXT
) RETURNS FLOAT AS $$
DECLARE
    v_phi FLOAT;
    v_rho FLOAT;
    v_surprise FLOAT;
    v_resonance_score FLOAT;
BEGIN
    -- Get motif resonance values
    SELECT m.phi, m.rho, COALESCE((m.telemetry->>'surprise')::float, 0.0)
    INTO v_phi, v_rho, v_surprise
    FROM AD_strands h
    LEFT JOIN AD_strands m ON h.hypothesis_id = m.motif_id
    WHERE h.id = p_hypothesis_id;
    
    -- Calculate resonance score: φ · ρ · surprise
    v_resonance_score := COALESCE(v_phi, 0.0) * COALESCE(v_rho, 1.0) * COALESCE(v_surprise, 0.0);
    
    RETURN v_resonance_score;
END;
$$ LANGUAGE plpgsql;
