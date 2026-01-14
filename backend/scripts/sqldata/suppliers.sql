-- MySQL dump 10.13  Distrib 8.0.44, for Win64 (x86_64)
--
-- Host: 127.0.0.1    Database: ultrafinu_promanage
-- ------------------------------------------------------
-- Server version	8.0.44

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Table structure for table `suppliers`
--

DROP TABLE IF EXISTS `suppliers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `suppliers` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `has_api` tinyint(1) DEFAULT '0',
  `bill_type` enum('rent','utilities','telecom','ebloc','other') COLLATE utf8mb4_unicode_ci DEFAULT 'utilities',
  `extraction_pattern_supplier` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `name` (`name`),
  KEY `idx_suppliers_name` (`name`),
  KEY `idx_suppliers_pattern` (`extraction_pattern_supplier`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `suppliers`
--

LOCK TABLES `suppliers` WRITE;
/*!40000 ALTER TABLE `suppliers` DISABLE KEYS */;
INSERT INTO `suppliers` VALUES ('0','[Pattern-based Supplier]',0,'other',NULL,'2026-01-10 15:30:59'),('00ca9f3c-93a9-40b0-940d-416739d12d6e','Vodafone',0,'telecom','vodafone','2025-12-31 11:17:45'),('07b31939-5944-4f5e-b982-5ee9e1dd1e67','Engie',0,'utilities','engie','2026-01-05 17:58:31'),('1e0537e9-4242-4e5e-82e2-6fad9e08494f','E-bloc',1,'ebloc','e-bloc','2025-12-31 11:17:45'),('5f923979-987f-4bb8-838b-786ee4e275ee','Engie Gaze',0,'utilities','engie.gaz','2026-01-02 13:26:46'),('91a20e9c-ca6a-4a27-91f5-51cae6e1903f','PPC Gaze',0,'utilities','ppc.gaz','2026-01-11 13:41:47'),('dc09419b-212a-4e3d-914e-17f083911fc5','Hidroelectrica',0,'utilities','hidroelectrica','2025-12-31 11:17:45'),('ee8a274b-837f-4d72-860e-5aad97487958','Digi',0,'utilities','digi','2025-12-31 11:17:45'),('f9363812-3e73-4edb-b26f-af721cfdefc6','Telekom',0,'telecom','telekom','2026-01-12 18:04:26');
/*!40000 ALTER TABLE `suppliers` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-14 22:00:38
