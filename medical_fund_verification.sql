-- Drop the database if it exists (optional, for resetting)
DROP DATABASE IF EXISTS medical_fund_db;

-- Create the database
CREATE DATABASE medical_fund_db;
USE medical_fund_db;

-- Create the users table
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    username VARCHAR(255) NOT NULL UNIQUE,
    email VARCHAR(255) NOT NULL UNIQUE,
    password VARCHAR(255) NOT NULL,
    role ENUM('user', 'admin') NOT NULL DEFAULT 'user',
    INDEX idx_email (email)  -- Index for faster email lookups
);

-- Create the fund_requests table
CREATE TABLE fund_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    funding_goal FLOAT NOT NULL DEFAULT 0.0,
    raised FLOAT NOT NULL DEFAULT 0.0,
    status ENUM('pending', 'approved', 'rejected') NOT NULL DEFAULT 'pending',
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),  -- Index for faster lookups by user_id
    INDEX idx_status (status)     -- Index for faster filtering by status
);

-- Create the request_documents table
CREATE TABLE request_documents (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    filename VARCHAR(255) NOT NULL,
    FOREIGN KEY (request_id) REFERENCES fund_requests(id) ON DELETE CASCADE,
    INDEX idx_request_id (request_id)  -- Index for faster lookups by request_id
);

-- Create the donations table
CREATE TABLE donations (
    id INT AUTO_INCREMENT PRIMARY KEY,
    request_id INT NOT NULL,
    donor_id INT NOT NULL,
    amount FLOAT NOT NULL,
    donation_message TEXT,
    donated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (request_id) REFERENCES fund_requests(id) ON DELETE CASCADE,
    FOREIGN KEY (donor_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_request_id (request_id),  -- Index for faster lookups by request_id
    INDEX idx_donor_id (donor_id)      -- Index for faster lookups by donor_id
);

-- Create the user_activity_logs table (new)
CREATE TABLE user_activity_logs (
    id INT AUTO_INCREMENT PRIMARY KEY,
    user_id INT NOT NULL,
    activity_type ENUM('login', 'logout', 'fund_request', 'donation') NOT NULL,
    activity_description VARCHAR(255),
    activity_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE,
    INDEX idx_user_id (user_id),  -- Index for faster lookups by user_id
    INDEX idx_activity_timestamp (activity_timestamp)  -- Index for faster filtering by timestamp
);

-- Start a transaction for inserting sample data
START TRANSACTION;

-- Insert sample users (using INSERT IGNORE to avoid duplicates)
INSERT IGNORE INTO users (username, email, password, role) VALUES
('admin', 'ravidynamo1924@gmail.com', 'Ravidhiya@1924', 'admin'),
('john_doe', 'john@example.com', 'password123', 'user'),
('jane_smith', 'jane@example.com', 'password456', 'user'),
('bob_jones', 'bob@example.com', 'password789', 'user'),
('alice_brown', 'alice@example.com', 'password101', 'user'),
('mary_jane', 'mary@example.com', 'password202', 'user');

-- Insert sample fund requests
INSERT IGNORE INTO fund_requests (user_id, title, description, funding_goal, raised, status, created_at) VALUES
(2, 'Surgery Funding', 'Need funds for an urgent surgery.', 5000.0, 0.0, 'pending', '2025-03-15 10:00:00'),
(2, 'Cancer Treatment', 'Seeking support for chemotherapy sessions.', 10000.0, 2500.0, 'approved', '2025-03-10 09:00:00'),
(3, 'Medical Equipment', 'Need funds to purchase a wheelchair.', 2000.0, 0.0, 'rejected', '2025-03-12 14:30:00'),
(3, 'Therapy Sessions', 'Funding for physical therapy after an accident.', 3000.0, 800.0, 'approved', '2025-03-18 11:00:00'),
(4, 'Emergency Surgery', 'Urgent funds needed for a life-saving surgery.', 7000.0, 0.0, 'pending', '2025-03-20 08:00:00'),
(5, 'Dental Surgery', 'Need funds for a dental procedure.', 4000.0, 1500.0, 'approved', '2025-03-21 09:00:00');

-- Insert sample documents for the fund requests
INSERT IGNORE INTO request_documents (request_id, filename) VALUES
(1, 'medical_bill.pdf'),
(1, 'prescription.jpg'),
(2, 'treatment_plan.pdf'),
(3, 'equipment_invoice.pdf'),
(4, 'therapy_receipt.pdf'),
(5, 'surgery_estimate.pdf'),
(6, 'dental_report.pdf');

-- Insert sample donations (for approved requests)
INSERT IGNORE INTO donations (request_id, donor_id, amount, donation_message, donated_at) VALUES
(2, 4, 1000.0, 'Wishing you a speedy recovery!', '2025-03-11 15:00:00'),  -- Bob donates to John's cancer treatment
(2, 3, 1000.0, 'Stay strong!', '2025-03-12 16:00:00'),  -- Jane donates to John's cancer treatment
(2, 5, 500.0, 'Hope this helps!', '2025-03-13 09:00:00'),  -- Alice donates to John's cancer treatment
(4, 2, 500.0, 'Get well soon!', '2025-03-19 09:00:00'),  -- John donates to Jane's therapy sessions
(4, 5, 300.0, 'Sending my support!', '2025-03-19 10:00:00'),  -- Alice donates to Jane's therapy sessions
(6, 2, 700.0, 'Wishing you the best!', '2025-03-21 10:00:00'),  -- John donates to Alice's dental surgery
(6, 3, 800.0, 'Hope this helps with your recovery!', '2025-03-21 11:00:00');  -- Jane donates to Alice's dental surgery

-- Insert sample user activity logs (e.g., login history)
INSERT IGNORE INTO user_activity_logs (user_id, activity_type, activity_description, activity_timestamp) VALUES
(1, 'login', 'Admin logged in', '2025-03-21 10:00:00'),
(2, 'login', 'John logged in', '2025-03-21 10:05:00'),
(3, 'login', 'Jane logged in', '2025-03-21 10:10:00'),
(4, 'donation', 'Bob donated to Cancer Treatment', '2025-03-11 15:00:00'),
(2, 'fund_request', 'John submitted Cancer Treatment request', '2025-03-10 09:00:00');

-- Commit the transaction
COMMIT;