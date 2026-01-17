-- Migration: Add DX trajectory types to check_trajectory_type constraint
-- DX buys are binary outcomes (success = led to trim, failure = no trim after)

ALTER TABLE position_trajectories DROP CONSTRAINT IF EXISTS check_trajectory_type;

ALTER TABLE position_trajectories ADD CONSTRAINT check_trajectory_type 
    CHECK (trajectory_type IN (
        'immediate_failure', 
        'trim_but_loss', 
        'trimmed_winner', 
        'clean_winner',
        'dx_success',    -- DX buy that led to subsequent trim
        'dx_failure'     -- DX buy with no subsequent trim
    ));

COMMENT ON COLUMN position_trajectories.trajectory_type IS 
'Six trajectory types:
- immediate_failure: S0 before reaching S3, ROI <= 0
- trim_but_loss: Reached S3, trimmed, still lost (ROI <= 0)  
- trimmed_winner: Reached S3, trimmed, profit (ROI > 0)
- clean_winner: Reached S3, profit (ROI > 0)
- dx_success: Individual DX buy that led to subsequent trim
- dx_failure: Individual DX buy with no subsequent trim';
