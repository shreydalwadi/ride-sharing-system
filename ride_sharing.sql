-- =========================================
-- Ride Sharing System Database
-- Mandatory OTP Authentication Version
-- =========================================

CREATE DATABASE IF NOT EXISTS ride_sharing;
USE ride_sharing;

-- Reset tables
DROP TABLE IF EXISTS ride_requests;
DROP TABLE IF EXISTS rides;
DROP TABLE IF EXISTS users;

-- ---------------- USERS TABLE ----------------
CREATE TABLE users (
    id INT AUTO_INCREMENT PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    mobile VARCHAR(10) NOT NULL UNIQUE,
    email VARCHAR(100) NOT NULL UNIQUE,
    password VARCHAR(100) NOT NULL,
    role ENUM('passenger','driver','admin') NOT NULL,
    vehicle_number VARCHAR(20),

    -- OTP AUTH FIELDS
    otp VARCHAR(6),
    otp_expiry DATETIME,
    is_verified BOOLEAN DEFAULT FALSE
);

-- ---------------- RIDES TABLE ----------------
CREATE TABLE rides (
    id INT AUTO_INCREMENT PRIMARY KEY,
    driver_id INT NOT NULL,
    start_point VARCHAR(100) NOT NULL,
    end_point VARCHAR(100) NOT NULL,
    seats INT NOT NULL,
    ride_date DATE NOT NULL,
    ride_time TIME NOT NULL,
    status ENUM('Scheduled','Ongoing','Completed') DEFAULT 'Scheduled',
    FOREIGN KEY (driver_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- ---------------- RIDE REQUESTS TABLE ----------------
CREATE TABLE ride_requests (
    id INT AUTO_INCREMENT PRIMARY KEY,
    ride_id INT NOT NULL,
    passenger_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'Pending',
    message VARCHAR(255),
    rating INT,
    FOREIGN KEY (ride_id) REFERENCES rides(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE,
    FOREIGN KEY (passenger_id) REFERENCES users(id)
        ON DELETE CASCADE
        ON UPDATE CASCADE
);

-- ---------------- DEFAULT ADMIN ----------------
INSERT INTO users (name, mobile, email, password, role, is_verified)
VALUES 
(
    'System Admin','9999999999','admin@rideshare.com','admin','admin',TRUE
);

INSERT INTO users
(name, mobile, email, password, role, vehicle_number, is_verified)
VALUES
(
    'sneh','9824882580','12302040701178@mbit.edu.in','123','driver','GJ01AB1234',TRUE
);
INSERT INTO users
(name, mobile, email, password, role, vehicle_number, is_verified)
VALUES
(
    'shrey','8758623406','12302080601148@adit.ac.in','123','passenger',NULL,TRUE
);
