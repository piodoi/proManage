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
-- Table structure for table `properties`
--

DROP TABLE IF EXISTS `properties`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `properties` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `landlord_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `address` text COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_properties_landlord` (`landlord_id`),
  KEY `idx_properties_name` (`name`),
  CONSTRAINT `properties_ibfk_1` FOREIGN KEY (`landlord_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `properties`
--

LOCK TABLES `properties` WRITE;
/*!40000 ALTER TABLE `properties` DISABLE KEYS */;
INSERT INTO `properties` VALUES ('1305a3b8-2509-4cf4-a93a-fe9a868de4c6','57ca9597-6a30-4775-bc89-71243d828a98','Str. Plutonier Radu Gheorghe Sc: A Ap: 25','Str. Plutonier Radu Gheorghe','2025-12-31 11:20:21'),('3e404c0f-2361-48c7-b2b8-45d7e7cf3964','748b8c6a-af3b-4328-b087-277a76d1c930','Home','First','2026-01-03 16:46:43'),('5ad35b8e-e254-435b-bfbc-be5f3777a2dc','57ca9597-6a30-4775-bc89-71243d828a98','1 Decembrie Nr 17','Loc Joaca','2026-01-08 11:51:35'),('7b590e84-affd-4310-962d-d889c42ed137','57ca9597-6a30-4775-bc89-71243d828a98','Vlad Tepes 97, Tanganu Ilfov','Vlad Tepes 97','2025-12-31 15:27:03'),('a3b56669-a657-481c-b57f-52fd94f1d7e4','57ca9597-6a30-4775-bc89-71243d828a98','Strada Trapezului nr.2 Bl: M6 Sc: 2 Ap: 53','Strada Trapezului nr.2','2025-12-31 11:20:21'),('b2c07414-e2bb-4515-b568-5f3dd596f14d','57ca9597-6a30-4775-bc89-71243d828a98','Spineni nr.1, sector 4,Bucuresti Sc: A Ap: 5','Spineni nr.1, sector 4,Bucuresti','2025-12-31 11:20:21'),('e06b83db-1331-4137-a687-3058b969ccae','57ca9597-6a30-4775-bc89-71243d828a98','Str. Mizil nr.57 Sc: C2/1 Ap: 8','Str. Mizil nr.57','2025-12-31 11:20:21');
/*!40000 ALTER TABLE `properties` ENABLE KEYS */;
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
