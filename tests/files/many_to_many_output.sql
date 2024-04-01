CREATE TABLE `Parent`
(
    `id` INT AUTO_INCREMENT NOT NULL,
    `code` VARCHAR(36) NOT NULL,
    `children` JSON NULL,
    PRIMARY KEY (id)
);


--
CREATE TABLE `Child`
(
    `id` INT AUTO_INCREMENT NOT NULL,
    `code` VARCHAR(36) NOT NULL,
    `parents` JSON NULL,
    PRIMARY KEY (id)
);


-- many-to-many assoc table
CREATE TABLE `Child_Parent_assoc`
(
    `id` int AUTO_INCREMENT NOT NULL UNIQUE COMMENT '主键',
    `Child_code` VARCHAR(36) NULL COMMENT 'Child的code字段',
    `Parent_code` VARCHAR(36) NULL COMMENT 'Parent的code字段',
    PRIMARY KEY (id)
) COMMENT = '__多对多关系'
  CHARSET = utf8mb4
  COLLATE = utf8mb4_0900_as_ci;
