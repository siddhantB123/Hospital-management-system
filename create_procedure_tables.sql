-- Create procedure table
CREATE TABLE procedure (
    procedure_id NUMBER PRIMARY KEY,
    name VARCHAR2(100) NOT NULL,
    cost NUMBER(10,2) NOT NULL
);

-- Create sequence for procedure_id
CREATE SEQUENCE procedure_seq
    START WITH 1
    INCREMENT BY 1
    NOCACHE
    NOCYCLE;

-- Create undergoes table
CREATE TABLE undergoes (
    patient_id NUMBER NOT NULL,
    procedure_id NUMBER NOT NULL,
    emp_id NUMBER NOT NULL,
    date_undergoes DATE DEFAULT SYSDATE,
    PRIMARY KEY (patient_id, procedure_id, date_undergoes),
    FOREIGN KEY (patient_id) REFERENCES patient(patient_id),
    FOREIGN KEY (procedure_id) REFERENCES procedure(procedure_id),
    FOREIGN KEY (emp_id) REFERENCES physician(emp_id)
);

-- Insert sample procedures
INSERT INTO procedure (procedure_id, name, cost) VALUES (procedure_seq.NEXTVAL, 'X-Ray', 500.00);
INSERT INTO procedure (procedure_id, name, cost) VALUES (procedure_seq.NEXTVAL, 'MRI Scan', 2000.00);
INSERT INTO procedure (procedure_id, name, cost) VALUES (procedure_seq.NEXTVAL, 'Blood Test', 300.00);
INSERT INTO procedure (procedure_id, name, cost) VALUES (procedure_seq.NEXTVAL, 'ECG', 400.00);
INSERT INTO procedure (procedure_id, name, cost) VALUES (procedure_seq.NEXTVAL, 'Ultrasound', 800.00);

COMMIT; 