-- Add referral system columns to users table

-- Referral tracking for users
ALTER TABLE users ADD COLUMN referral_code VARCHAR(20) UNIQUE;
ALTER TABLE users ADD COLUMN referred_by VARCHAR(36);
ALTER TABLE users ADD COLUMN referral_reward_applied BOOLEAN DEFAULT FALSE;
ALTER TABLE users ADD COLUMN referral_signup_date TIMESTAMP;

-- Create referral_rewards table to track all referrals and rewards
CREATE TABLE IF NOT EXISTS referral_rewards (
    id VARCHAR(36) PRIMARY KEY,
    referrer_id VARCHAR(36) NOT NULL,
    referred_user_id VARCHAR(36) NOT NULL,
    referred_user_email VARCHAR(255) NOT NULL,
    signup_date TIMESTAMP NOT NULL,
    subscription_date TIMESTAMP,
    reward_applied BOOLEAN DEFAULT FALSE,
    reward_applied_date TIMESTAMP,
    reward_type VARCHAR(50) DEFAULT 'skip_month',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (referrer_id) REFERENCES users(id) ON DELETE CASCADE,
    FOREIGN KEY (referred_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE INDEX idx_referral_rewards_referrer ON referral_rewards(referrer_id);
CREATE INDEX idx_referral_rewards_referred ON referral_rewards(referred_user_id);
CREATE INDEX idx_referral_rewards_pending ON referral_rewards(reward_applied, subscription_date);

-- For PostgreSQL, use the following instead:
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_code VARCHAR(20) UNIQUE;
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS referred_by VARCHAR(36);
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_reward_applied BOOLEAN DEFAULT FALSE;
-- ALTER TABLE users ADD COLUMN IF NOT EXISTS referral_signup_date TIMESTAMP;
