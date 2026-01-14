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
-- Table structure for table `renters`
--

DROP TABLE IF EXISTS `renters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `renters` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `property_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(50) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rent_day` int DEFAULT NULL,
  `start_contract_date` date DEFAULT NULL,
  `rent_amount_eur` float DEFAULT NULL,
  `access_token` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `access_token` (`access_token`),
  KEY `idx_renters_property` (`property_id`),
  KEY `idx_renters_token` (`access_token`),
  KEY `idx_renters_email` (`email`),
  CONSTRAINT `renters_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `renters`
--

LOCK TABLES `renters` WRITE;
/*!40000 ALTER TABLE `renters` DISABLE KEYS */;
INSERT INTO `renters` VALUES ('5090eafa-f0b3-46d3-804e-06bffb59f37a','e06b83db-1331-4137-a687-3058b969ccae','Miruna Pricopie',NULL,NULL,10,NULL,405,'aeb52050-a314-467f-a77c-65e91abb3102','2026-01-01 19:57:56'),('8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','Zoahib',NULL,NULL,20,NULL,360,'74a4a9ad-5b98-4649-8372-c7ff767c5f4f','2026-01-01 20:29:29'),('bf153da6-17f3-4146-ba80-54fd9ece7621','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','Sojib',NULL,NULL,10,NULL,170,'24e267fd-e913-4049-ae10-ecb3b75b3251','2026-01-01 20:30:45'),('dd205ad6-b2da-413e-957b-af790c7798d8','b2c07414-e2bb-4515-b568-5f3dd596f14d','Andrei Zdrali',NULL,'+40731733991',1,NULL,360,'e49c06f9-85fb-44dc-9bb8-63b57aa6ba70','2026-01-01 19:53:33'),('e893c57c-f607-4a7a-a1e4-e345176997af','3e404c0f-2361-48c7-b2b8-45d7e7cf3964','place',NULL,NULL,5,NULL,100,'e84a393b-3b2d-48f4-9b97-536dc337b721','2026-01-03 16:47:05'),('eefb3318-cdf2-48f2-9c97-63cde1e563bf','7b590e84-affd-4310-962d-d889c42ed137','test rent',NULL,'+40723127785',1,NULL,100,'f9e8b0aa-500e-4cf6-b5f4-5a63c6e68f17','2026-01-09 17:38:09'),('f938c711-3209-49df-8580-13f9c96b9fbf','a3b56669-a657-481c-b57f-52fd94f1d7e4','Hraniceru Viorel',NULL,'+40736739166',25,NULL,460,'f725a9cf-cbd6-403a-844a-43a7a1c9d044','2026-01-01 19:23:17');
/*!40000 ALTER TABLE `renters` ENABLE KEYS */;
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
