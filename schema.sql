-- Fresh empty MySQL database only. This is not an upgrade migration.
CREATE TABLE zamestnanci (
    idZamestnance INT PRIMARY KEY,
    jmeno VARCHAR(100) NOT NULL,
    prijmeni VARCHAR(100) NOT NULL,
    login VARCHAR(100) NOT NULL UNIQUE,
    admin BOOLEAN NOT NULL DEFAULT FALSE,
    heslo VARCHAR(255) NOT NULL,
    email VARCHAR(255) NOT NULL,
    divize VARCHAR(100) NOT NULL,
    oddeleni VARCHAR(100) NOT NULL
) ENGINE=InnoDB;

CREATE TABLE auta (
    id INT AUTO_INCREMENT PRIMARY KEY,
    vin VARCHAR(17) NOT NULL UNIQUE,
    spz VARCHAR(20) NOT NULL UNIQUE,
    znacka VARCHAR(100) NOT NULL,
    model VARCHAR(100) NOT NULL,
    rokVyroby INT NOT NULL,
    najetoKm INT UNSIGNED NOT NULL
) ENGINE=InnoDB;

CREATE TABLE rezervace (
    id INT AUTO_INCREMENT PRIMARY KEY,
    idZamestnance INT NOT NULL,
    jmeno VARCHAR(100) NOT NULL,
    prijmeni VARCHAR(100) NOT NULL,
    divize VARCHAR(100) NOT NULL,
    oddeleni VARCHAR(100) NOT NULL,
    idAuta INT NOT NULL,
    spz VARCHAR(20) NOT NULL,
    stavRezervace VARCHAR(100) NOT NULL,
    prevzetiDne DATE NOT NULL,
    odevzdaniDne DATE NOT NULL,
    kmPredJizdou INT UNSIGNED NULL,
    kmPoJizde INT UNSIGNED NULL,
    najetoKm INT UNSIGNED NULL,
    poskozeni TEXT NOT NULL,
    INDEX reservation_overlap (idAuta, prevzetiDne, odevzdaniDne),
    FOREIGN KEY (idZamestnance) REFERENCES zamestnanci(idZamestnance),
    FOREIGN KEY (idAuta) REFERENCES auta(id),
    CHECK (odevzdaniDne >= prevzetiDne)
) ENGINE=InnoDB;
