-- Drop the database if it exists
DROP DATABASE IF EXISTS leathersense;

-- Create the database
CREATE DATABASE leathersense;

-- Use the created database
USE leathersense;

-- Drop the actuator table if it exists
DROP TABLE IF EXISTS actuator;

-- Create the actuator table
CREATE TABLE actuator (
    ip_address VARCHAR(45) PRIMARY KEY,
    type VARCHAR(45),
    status VARCHAR(45) DEFAULT 'OFF',
    registration_timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Drop the telemetry table if it exists
DROP TABLE IF EXISTS telemetry;

-- Create the telemetry table
CREATE TABLE telemetry (
    id INT AUTO_INCREMENT PRIMARY KEY,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    type VARCHAR(45),
    value FLOAT
);
