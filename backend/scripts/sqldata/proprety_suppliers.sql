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
-- Table structure for table `property_suppliers`
--

DROP TABLE IF EXISTS `property_suppliers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_suppliers` (
  `id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `property_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `supplier_id` varchar(36) COLLATE utf8mb4_unicode_ci NOT NULL,
  `extraction_pattern_supplier` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contract_id` varchar(100) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `direct_debit` tinyint(1) DEFAULT '0',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `idx_ps_property_supplier` (`property_id`,`supplier_id`),
  KEY `idx_ps_property` (`property_id`),
  KEY `idx_ps_supplier` (`supplier_id`),
  KEY `idx_ps_contract` (`contract_id`),
  KEY `idx_ps_extraction_pattern` (`extraction_pattern_supplier`),
  CONSTRAINT `property_suppliers_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE,
  CONSTRAINT `property_suppliers_ibfk_2` FOREIGN KEY (`supplier_id`) REFERENCES `suppliers` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `property_suppliers`
--

LOCK TABLES `property_suppliers` WRITE;
/*!40000 ALTER TABLE `property_suppliers` DISABLE KEYS */;
INSERT INTO `property_suppliers` VALUES ('07ecbc7b-5885-40eb-b596-e34ed33adb3b','5ad35b8e-e254-435b-bfbc-be5f3777a2dc','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,NULL,1,'2026-01-08 11:52:16','2026-01-08 13:52:16'),('08cea347-a648-4bd3-8be7-c696410e63ab','e06b83db-1331-4137-a687-3058b969ccae','5f923979-987f-4bb8-838b-786ee4e275ee',NULL,'4001941859',0,'2026-01-02 13:30:12','2026-01-02 13:30:12'),('38fc9ea3-cb4c-4ae8-8dce-239f3fcf8ddb','7b590e84-affd-4310-962d-d889c42ed137','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'8000324406',1,'2025-12-31 16:01:21','2026-01-02 09:43:52'),('46286284-b44b-442c-bd6a-89737d3a4a6a','7b590e84-affd-4310-962d-d889c42ed137','0','PPC Energie S.A.','PEYIFCERN053002',1,'2026-01-10 13:55:47','2026-01-11 15:45:20'),('491e0ee8-7c77-49bb-82da-0540381dc2fe','b2c07414-e2bb-4515-b568-5f3dd596f14d','5f923979-987f-4bb8-838b-786ee4e275ee',NULL,'4001585793',1,'2026-01-05 15:24:35','2026-01-05 15:24:35'),('669c2977-e40d-48ba-b4e4-db35723e311a','a3b56669-a657-481c-b57f-52fd94f1d7e4','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'8000324423',1,'2025-12-31 15:31:52','2026-01-02 09:36:52'),('6df0773b-4127-44d9-be4e-2045d6365633','a3b56669-a657-481c-b57f-52fd94f1d7e4','ee8a274b-837f-4d72-860e-5aad97487958',NULL,NULL,1,'2026-01-02 09:22:42','2026-01-02 09:22:42'),('78ef93bb-4dad-43fe-9e32-75472b4ec672','7b590e84-affd-4310-962d-d889c42ed137','ee8a274b-837f-4d72-860e-5aad97487958',NULL,NULL,1,'2026-01-02 09:43:44','2026-01-02 09:43:44'),('8882643f-4def-4f8a-a6d8-f1ca49e83522','a3b56669-a657-481c-b57f-52fd94f1d7e4','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,'24477',0,'2026-01-03 20:45:54','2026-01-03 20:45:54'),('8a135809-7ea4-45eb-8ab1-aa0a26c34d76','a3b56669-a657-481c-b57f-52fd94f1d7e4','0','Telekom',NULL,0,'2026-01-12 07:57:32','2026-01-12 09:57:32'),('8ae4fd2e-7827-4652-af89-9b7f2dbd43e0','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,'141936',0,'2025-12-31 11:20:21','2025-12-31 11:20:21'),('9a51e17a-0b57-471c-9bfa-f38683575962','4351d460-63ae-4e9a-9bc7-65b792d77718','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,NULL,0,'2026-01-03 16:35:26','2026-01-03 16:35:26'),('9e39ce60-a853-4947-8d45-db94aa965042','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'8000970939',0,'2025-12-31 15:29:29','2025-12-31 15:29:29'),('9ee5decf-b072-4c91-8187-c9acced50d6c','e06b83db-1331-4137-a687-3058b969ccae','00ca9f3c-93a9-40b0-940d-416739d12d6e',NULL,NULL,1,'2026-01-02 09:09:47','2026-01-09 20:06:59'),('afc58013-a26a-4273-9aac-d5c62dc8c37d','e06b83db-1331-4137-a687-3058b969ccae','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,'A54BB6E',0,'2026-01-03 20:46:07','2026-01-03 20:46:07'),('c47db48f-d2b1-4291-8f1c-9ad096ee061f','b2c07414-e2bb-4515-b568-5f3dd596f14d','07b31939-5944-4f5e-b982-5ee9e1dd1e67',NULL,'115335242,',1,'2026-01-05 17:59:40','2026-01-05 17:59:51'),('d148ae3c-0e59-40d7-b476-36fcdcb8e4ea','e06b83db-1331-4137-a687-3058b969ccae','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'8000324444',0,'2025-12-31 15:35:58','2025-12-31 15:35:58'),('d7a6bc07-5888-412f-9120-618f1dee1766','5ad35b8e-e254-435b-bfbc-be5f3777a2dc','ee8a274b-837f-4d72-860e-5aad97487958',NULL,NULL,1,'2026-01-08 11:51:52','2026-01-08 13:51:52'),('f5ea83f7-daae-4879-aa84-100347f2ad41','b2c07414-e2bb-4515-b568-5f3dd596f14d','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,'A1FA387',0,'2026-01-03 20:06:21','2026-01-03 20:06:21');
/*!40000 ALTER TABLE `property_suppliers` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-01-14 22:00:37
