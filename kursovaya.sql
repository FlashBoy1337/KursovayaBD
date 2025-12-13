-- 1. СБРОС (Удаляем старое)
DROP TABLE IF EXISTS Order_Items CASCADE;
DROP TABLE IF EXISTS Production_Orders CASCADE;
DROP TABLE IF EXISTS Employees CASCADE;
DROP TABLE IF EXISTS Product_Composition CASCADE;
DROP TABLE IF EXISTS Products CASCADE;
DROP TABLE IF EXISTS Components CASCADE;
DROP TABLE IF EXISTS Materials CASCADE;
DROP FUNCTION IF EXISTS update_product_cost CASCADE;

-- 2. СОЗДАНИЕ ТАБЛИЦ
CREATE TABLE Materials (
    material_id SERIAL PRIMARY KEY,
    material_name VARCHAR(255) NOT NULL UNIQUE,
    unit_of_measurement VARCHAR(50) NOT NULL, 
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price > 0),
    stock_quantity INT NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0)
);

CREATE TABLE Components (
    component_id SERIAL PRIMARY KEY,
    component_name VARCHAR(255) NOT NULL UNIQUE,
    supplier VARCHAR(255),
    unit_price DECIMAL(10, 2) NOT NULL CHECK (unit_price > 0),
    stock_quantity INT NOT NULL DEFAULT 0 CHECK (stock_quantity >= 0)
);

CREATE TABLE Products (
    product_id SERIAL PRIMARY KEY,
    product_name VARCHAR(255) NOT NULL UNIQUE,
    description TEXT,
    selling_price DECIMAL(10, 2) NOT NULL CHECK (selling_price > 0),
    cost_price DECIMAL(10, 2) DEFAULT 0 
);

CREATE TABLE Product_Composition (
    composition_id SERIAL PRIMARY KEY,
    product_id INT NOT NULL,
    material_id INT,
    component_id INT,
    quantity DECIMAL(10, 3) NOT NULL CHECK (quantity > 0),
    FOREIGN KEY (product_id) REFERENCES Products(product_id) ON DELETE CASCADE,
    FOREIGN KEY (material_id) REFERENCES Materials(material_id),
    FOREIGN KEY (component_id) REFERENCES Components(component_id),
    CHECK ((material_id IS NOT NULL AND component_id IS NULL) OR (material_id IS NULL AND component_id IS NOT NULL))
);

CREATE TABLE Employees (
    employee_id SERIAL PRIMARY KEY,
    first_name VARCHAR(100) NOT NULL,
    last_name VARCHAR(100) NOT NULL,
    position VARCHAR(100) NOT NULL,
    hire_date DATE NOT NULL DEFAULT CURRENT_DATE
);

CREATE TABLE Production_Orders (
    order_id SERIAL PRIMARY KEY,
    order_date DATE NOT NULL DEFAULT CURRENT_DATE,
    deadline_date DATE NOT NULL,
    status VARCHAR(50) NOT NULL DEFAULT 'Pending' CHECK (status IN ('Pending', 'In Progress', 'Completed', 'Cancelled')),
    assigned_employee_id INT,
    FOREIGN KEY (assigned_employee_id) REFERENCES Employees(employee_id)
);

CREATE TABLE Order_Items (
    item_id SERIAL PRIMARY KEY,
    order_id INT NOT NULL,
    product_id INT NOT NULL,
    quantity_to_produce INT NOT NULL CHECK (quantity_to_produce > 0),
    FOREIGN KEY (order_id) REFERENCES Production_Orders(order_id) ON DELETE CASCADE,
    FOREIGN KEY (product_id) REFERENCES Products(product_id)
);

-- 3. ВСТАВКА ДАННЫХ (ПОКА БЕЗ ТРИГГЕРА!)
INSERT INTO Materials (material_name, unit_of_measurement, unit_price, stock_quantity) VALUES
('ДСП Дуб 16мм', 'кв.м', 450.00, 100),
('ДСП Белый 16мм', 'кв.м', 400.00, 150),
('Кромка ПВХ', 'м', 20.00, 1000),
('Лак мебельный', 'л', 800.00, 50);

INSERT INTO Components (component_name, supplier, unit_price, stock_quantity) VALUES
('Ручка-скоба', 'OOO Фурнитура', 60.00, 200),
('Петля накладная', 'Hettich', 45.00, 400),
('Направляющие для ящиков', 'Boyard', 150.00, 100),
('Конфирмат (евровинт)', 'Крепеж-Опт', 2.00, 5000),
('Ножка регулируемая', 'Крепеж-Опт', 15.00, 600);

INSERT INTO Products (product_name, description, selling_price) VALUES
('Шкаф "Стандарт"', 'Шкаф распашной, 2 двери', 6500.00),
('Стол компьютерный', 'Стол с 3 ящиками', 4200.00),
('Тумба прикроватная', 'Малая тумба', 1800.00);

INSERT INTO Product_Composition (product_id, material_id, quantity) VALUES 
(1, 1, 4.5), (1, 3, 10.0), (2, 2, 3.0), (2, 3, 8.0), (3, 1, 1.2);

INSERT INTO Product_Composition (product_id, component_id, quantity) VALUES 
(1, 1, 2), (1, 2, 4), (1, 4, 30), (1, 5, 4),
(2, 3, 3), (2, 1, 3), (2, 4, 25),
(3, 1, 1), (3, 3, 2);

INSERT INTO Employees (first_name, last_name, position) VALUES
('Алексей', 'Смирнов', 'Сборщик'), ('Мария', 'Иванова', 'Технолог');

INSERT INTO Production_Orders (order_date, deadline_date, status, assigned_employee_id) VALUES
('2023-10-01', '2023-10-10', 'Completed', 1),
('2023-11-01', '2023-11-15', 'In Progress', 1);

INSERT INTO Order_Items (order_id, product_id, quantity_to_produce) VALUES
(1, 3, 10), (2, 1, 2), (2, 2, 1);

-- 4. ТЕПЕРЬ ВКЛЮЧАЕМ ТРИГГЕР (Когда данные уже внутри)
CREATE OR REPLACE FUNCTION update_product_cost() RETURNS TRIGGER AS $$
BEGIN
    UPDATE Products
    SET cost_price = (
        SELECT COALESCE(SUM(pc.quantity * COALESCE(m.unit_price, c.unit_price)), 0)
        FROM Product_Composition pc
        LEFT JOIN Materials m ON pc.material_id = m.material_id
        LEFT JOIN Components c ON pc.component_id = c.component_id
        WHERE pc.product_id = COALESCE(NEW.product_id, OLD.product_id)
    )
    WHERE product_id = COALESCE(NEW.product_id, OLD.product_id);
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trg_update_cost
AFTER INSERT OR UPDATE OR DELETE ON Product_Composition
FOR EACH ROW
EXECUTE FUNCTION update_product_cost();

-- 5. ПРИНУДИТЕЛЬНО ОБНОВЛЯЕМ ЦЕНЫ (Чтобы они посчитались для уже добавленных строк)
UPDATE Products p
SET cost_price = (
    SELECT COALESCE(SUM(pc.quantity * COALESCE(m.unit_price, c.unit_price)), 0)
    FROM Product_Composition pc
    LEFT JOIN Materials m ON pc.material_id = m.material_id
    LEFT JOIN Components c ON pc.component_id = c.component_id
    WHERE pc.product_id = p.product_id
);

-- 6. VIEWS (ПРЕДСТАВЛЕНИЯ)
CREATE OR REPLACE VIEW v_low_stock AS
SELECT material_name, stock_quantity FROM Materials WHERE stock_quantity < 50;

CREATE OR REPLACE VIEW v_product_recipe AS
SELECT p.product_name, COALESCE(m.material_name, c.component_name) AS resource, pc.quantity
FROM Product_Composition pc
JOIN Products p ON pc.product_id = p.product_id
LEFT JOIN Materials m ON pc.material_id = m.material_id
LEFT JOIN Components c ON pc.component_id = c.component_id;