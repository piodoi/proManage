-- MySQL dump 10.13  Distrib 8.0.44, for Linux (x86_64)
--
-- Host: 127.0.0.1    Database: ultrafinu_promanage
-- ------------------------------------------------------
-- Server version	8.0.44-google

/*!40101 SET @OLD_CHARACTER_SET_CLIENT=@@CHARACTER_SET_CLIENT */;
/*!40101 SET @OLD_CHARACTER_SET_RESULTS=@@CHARACTER_SET_RESULTS */;
/*!40101 SET @OLD_COLLATION_CONNECTION=@@COLLATION_CONNECTION */;
/*!50503 SET NAMES utf8mb4 */;
/*!40103 SET @OLD_TIME_ZONE=@@TIME_ZONE */;
/*!40103 SET TIME_ZONE='+00:00' */;
/*!40014 SET @OLD_UNIQUE_CHECKS=@@UNIQUE_CHECKS, UNIQUE_CHECKS=0 */;
/*!40014 SET @OLD_FOREIGN_KEY_CHECKS=@@FOREIGN_KEY_CHECKS, FOREIGN_KEY_CHECKS=0 */;
/*!40101 SET @OLD_SQL_MODE=@@SQL_MODE, SQL_MODE='NO_AUTO_VALUE_ON_ZERO' */;
/*!40111 SET @OLD_SQL_NOTES=@@SQL_NOTES, SQL_NOTES=0 */;

--
-- Current Database: `ultrafinu_promanage`
--

CREATE DATABASE /*!32312 IF NOT EXISTS*/ `ultrafinu_promanage` /*!40100 DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci */ /*!80016 DEFAULT ENCRYPTION='N' */;

USE `ultrafinu_promanage`;

--
-- Table structure for table `bills`
--

DROP TABLE IF EXISTS `bills`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `bills` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `property_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `renter_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `property_supplier_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bill_type` enum('rent','utilities','telecom','ebloc','other') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `description` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` float NOT NULL,
  `currency` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'RON',
  `due_date` datetime NOT NULL,
  `bill_date` datetime DEFAULT NULL,
  `legal_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iban` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `bill_number` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `extraction_pattern_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contract_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `payment_details` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  `status` enum('pending','paid','overdue') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `source_email_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  KEY `idx_bills_property` (`property_id`),
  KEY `idx_bills_renter` (`renter_id`),
  KEY `idx_bills_due_date` (`due_date`),
  KEY `idx_bills_status` (`status`),
  KEY `idx_bills_type` (`bill_type`),
  KEY `idx_bills_contract` (`contract_id`),
  KEY `idx_bills_property_due` (`property_id`,`due_date`),
  KEY `idx_bills_property_status` (`property_id`,`status`),
  KEY `idx_bills_property_supplier` (`property_supplier_id`),
  CONSTRAINT `bills_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `bills`
--

LOCK TABLES `bills` WRITE;
/*!40000 ALTER TABLE `bills` DISABLE KEYS */;
INSERT INTO `bills` VALUES ('00945337-fbbb-4c5b-b0a3-2697c1d78b60','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'491e0ee8-7c77-49bb-82da-0540381dc2fe','utilities','Engie Gaze',152.01,'RON','2026-04-22 00:00:00','2026-03-23 00:00:00','ENGIE Romania S.A. Sediul social: B-dul Mărăşeşti nr. 4 -6, sector 4,','RO40RZBR0000060010660361','11218110384',NULL,'4001585793',NULL,'paid',NULL,'2026-03-24 17:58:37'),('02416db0-5d62-451d-9f55-9472556c7b2e','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'ebloc','E-Bloc',0,'RON','2026-01-04 09:07:47',NULL,NULL,NULL,'Noiembrie 2025 Ap.53',NULL,'A000000',NULL,'paid',NULL,'2026-01-04 09:08:20'),('07ab4844-c4ec-4c10-a3fb-5d431ba51466','e06b83db-1331-4137-a687-3058b969ccae','5090eafa-f0b3-46d3-804e-06bffb59f37a',NULL,'rent','Ianuarie 2026',405,'EUR','2026-01-08 00:00:00',NULL,NULL,NULL,'01',NULL,NULL,NULL,'paid',NULL,'2026-01-03 17:44:42'),('07ba89f3-b19e-4787-866e-73bbc6ed792c','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','bf153da6-17f3-4146-ba80-54fd9ece7621',NULL,'rent','Martie 2026',170,'EUR','2026-03-10 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','03',NULL,NULL,NULL,'paid',NULL,'2026-02-11 18:28:19'),('0c8ea3f0-e98b-445e-88e3-45824c57739e','b2c07414-e2bb-4515-b568-5f3dd596f14d','dd205ad6-b2da-413e-957b-af790c7798d8','491e0ee8-7c77-49bb-82da-0540381dc2fe','utilities','Engie Gaze',143.98,'RON','2026-03-23 00:00:00','2026-02-20 00:00:00','ENGIE Romania S.A. Sediul social: B-dul Mărăşeşti nr. 4 -6, sector 4,','RO40RZBR0000060010660361','11703669612','engie.gaz','4001585793',NULL,'paid',NULL,'2026-02-20 18:19:39'),('149306a4-18e7-4cc2-b1a0-93cb3a6b768b','e06b83db-1331-4137-a687-3058b969ccae','5090eafa-f0b3-46d3-804e-06bffb59f37a','08cea347-a648-4bd3-8be7-c696410e63ab','utilities','Engie Gaze',276.38,'RON','2026-03-23 00:00:00','2026-02-20 00:00:00','ENGIE Romania S.A. Sediul social: B-dul Mărăşeşti nr. 4 -6, sector 4,','RO40RZBR0000060010660361','10421644454','engie.gaz','4001941859',NULL,'paid',NULL,'2026-02-20 18:20:14'),('1829b1fe-f11c-4a63-a9d7-90217ca50ffa','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'491e0ee8-7c77-49bb-82da-0540381dc2fe','utilities','Engie Gaze',184.74,'RON','2026-02-23 00:00:00','2026-01-23 00:00:00','ENGIE Romania S.A. Sediul social: B-dul Mărăşeşti nr. 4 -6, sector 4,','RO40RZBR0000060010660361','10619377681',NULL,'4001585793',NULL,'paid',NULL,'2026-01-23 22:04:03'),('1ae68411-37e7-4c05-88ff-0eb976eb2773','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff',NULL,'rent','February 2026',360,'EUR','2026-02-20 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'paid',NULL,'2026-01-22 08:03:36'),('1b21a7d5-4eab-4bc8-947b-2b1e7b7cd364','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,'8ae4fd2e-7827-4652-af89-9b7f2dbd43e0','ebloc','E-bloc',1152,'RON','2026-03-30 00:00:00','2026-03-04 00:00:00','Asociatia de Proprietari Bl. 12 Titan','RO40RNCB0089003747230001','IANUARIE 2026',NULL,'A4F80C5',NULL,'paid',NULL,'2026-03-04 07:59:52'),('1bd3859d-df1a-4d45-96f2-e21efe88fd0f','7b590e84-affd-4310-962d-d889c42ed137',NULL,'38fc9ea3-cb4c-4ae8-8dce-239f3fcf8ddb','utilities','Hidroelectrica',1250.45,'RON','2026-03-30 00:00:00','2026-02-12 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26101163968',NULL,'8000324406',NULL,'paid',NULL,'2026-02-13 08:46:15'),('1f318f22-5731-4685-bfa0-575f75965308','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,'9e39ce60-a853-4947-8d45-db94aa965042','utilities','Hidroelectrica',123.25,'RON','2026-04-27 00:00:00','2026-03-12 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26102797399',NULL,'Cod Cont Contract: 8000970939',NULL,'pending',NULL,'2026-03-12 18:38:10'),('1f9e03e7-42b7-47a3-8de7-8e07ea1b341a','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,'669c2977-e40d-48ba-b4e4-db35723e311a','utilities','Hidroelectrica',179.85,'RON','2026-03-30 00:00:00','2026-02-13 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26101623964',NULL,'Cod Cont Contract: 8000324423',NULL,'overdue',NULL,'2026-02-13 16:40:50'),('20256aa9-c070-4ff2-bb9a-64deca91496c','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'telecom','Telekom',33.69,'RON','2026-01-30 00:00:00','2026-01-16 00:00:00','TELEKOM ROMANIA MOBILE COMMUNICATIONS SA',NULL,'260100433013','telekom','99170010871410',NULL,'paid',NULL,'2026-01-19 15:53:10'),('220a3077-d18a-4556-897c-fc6b822a172a','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,NULL,'utilities','Hidroelectrica',124.68,'RON','2026-01-29 00:00:00',NULL,NULL,NULL,'25110727979','220e67e4-8d81-487c-8d35-639c3ac03a6b','8000970939',NULL,'paid',NULL,'2026-01-01 16:39:32'),('252cdf76-4e39-4af0-b89b-f7fc1180b302','5ad35b8e-e254-435b-bfbc-be5f3777a2dc',NULL,NULL,'utilities','Digi',30.5,'RON','2026-01-31 00:00:00',NULL,NULL,'RO51INGB0001000000018827','14743845','digi',NULL,NULL,'paid',NULL,'2026-01-09 16:31:28'),('28644440-3be8-42fa-a09c-2ee1de9bcf13','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,'669c2977-e40d-48ba-b4e4-db35723e311a','utilities','Hidroelectrica',-970.5,'RON','2026-04-27 00:00:00','2026-03-12 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26102850276','hidroelectrica','Cod Cont Contract: 8000324423','\"Client\"','paid',NULL,'2026-03-12 19:24:07'),('2b38f067-b449-4bef-b5a7-3c3a37d665d3','b2c07414-e2bb-4515-b568-5f3dd596f14d','dd205ad6-b2da-413e-957b-af790c7798d8',NULL,'rent','March 2026',360,'EUR','2026-03-01 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','03',NULL,NULL,NULL,'paid',NULL,'2026-02-02 18:04:20'),('2c1e45e0-bf41-44a9-9361-1f24bdb3a71f','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,'669c2977-e40d-48ba-b4e4-db35723e311a','utilities','Hidroelectrica',177.02,'RON','2026-03-09 00:00:00','2026-01-22 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26100303567',NULL,'8000324423',NULL,'paid',NULL,'2026-01-23 06:55:25'),('2d707079-9372-4d90-9562-d7dae1049184','e06b83db-1331-4137-a687-3058b969ccae',NULL,'9ee5decf-b072-4c91-8187-c9acced50d6c','utilities','Vodafone',44.65,'RON','2026-02-22 00:00:00','2026-02-02 00:00:00','Vodafone Romania S.A.','RO23INGB0001000000000222','VDF766811933',NULL,'271768784',NULL,'paid',NULL,'2026-02-06 09:53:41'),('364e5c7d-41d9-4742-a3fd-05c2c2c0d2e6','b2c07414-e2bb-4515-b568-5f3dd596f14d','dd205ad6-b2da-413e-957b-af790c7798d8',NULL,'rent','Aprilie 2026',360,'EUR','2026-04-01 00:00:00',NULL,NULL,'RO83REVO0000188367446976','04',NULL,NULL,NULL,'paid',NULL,'2026-03-04 07:59:29'),('3dd1cdbe-3ac1-4255-bcbb-7aff84ff9acf','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,'8ae4fd2e-7827-4652-af89-9b7f2dbd43e0','ebloc','e-bloc',1345,'RON','2026-05-03 00:00:00','2026-04-03 00:00:00','Asociatia de Proprietari Bl. 12 Titan','RO40RNCB0089003747230001','FEBRUARIE 2026',NULL,'A4F80C5',NULL,'pending',NULL,'2026-04-03 07:32:21'),('3e92a215-0157-4f00-b300-1e13593d5b1c','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'utilities','Hidroelectrica',31.27,'RON','2026-01-30 00:00:00',NULL,NULL,NULL,'25110944560','220e67e4-8d81-487c-8d35-639c3ac03a6b','8000324444',NULL,'paid',NULL,'2026-01-01 15:56:46'),('3f99dc3a-e956-4919-a766-a2613e9db478','e06b83db-1331-4137-a687-3058b969ccae',NULL,'d148ae3c-0e59-40d7-b476-36fcdcb8e4ea','utilities','Hidroelectrica',-8.71,'RON','2026-04-27 00:00:00','2026-03-12 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26102850277','hidroelectrica','Cod Cont Contract: 8000324444','\"Client\"','paid',NULL,'2026-03-12 19:36:28'),('44b154b7-06c5-431f-8b68-df510e8fc54d','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff',NULL,'rent','Aprilie 2026',370,'EUR','2026-04-20 00:00:00',NULL,NULL,'RO83REVO0000188367446976','04',NULL,NULL,NULL,'pending',NULL,'2026-03-21 17:05:35'),('45e5442b-d715-4c9f-99fc-b4c72775178a','e06b83db-1331-4137-a687-3058b969ccae',NULL,'afc58013-a26a-4273-9aac-d5c62dc8c37d','ebloc','E-bloc',148.43,'RON','2026-01-30 00:00:00','2026-01-12 00:00:00','sociatia de Proprietari Aleea Mizil Nr. 57','RO86INGB0000999909534657','NOIEMBRIE 2025',NULL,'A54BB6E',NULL,'paid',NULL,'2026-01-12 19:00:11'),('486755c0-3645-4354-8ca0-06184fd325fe','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'ebloc','E-bloc',139.54,'RON','2026-01-01 00:00:00',NULL,NULL,NULL,'Octombrie 2025 Ap.8',NULL,'68210',NULL,'paid',NULL,'2026-01-03 23:17:03'),('49b40785-5d6b-4d45-b972-a7b2988aaf78','b2c07414-e2bb-4515-b568-5f3dd596f14d','dd205ad6-b2da-413e-957b-af790c7798d8',NULL,'rent','February 2026',360,'EUR','2026-02-01 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'paid',NULL,'2026-01-09 17:40:13'),('4be40050-0763-4cbd-b5e9-2ea5b3292220','e06b83db-1331-4137-a687-3058b969ccae',NULL,'08cea347-a648-4bd3-8be7-c696410e63ab','utilities','Engie Gaze',305.6,'RON','2026-02-23 00:00:00','2026-01-22 00:00:00','ENGIE Romania S.A. Sediul social: B-dul Mărăşeşti nr. 4 -6, sector 4,','RO40RZBR0000060010660361','10325235949','engie.gaz','4001941859',NULL,'paid',NULL,'2026-01-23 10:52:11'),('4e9dce22-de3f-4a1b-83c0-82a7fc5f543c','a3b56669-a657-481c-b57f-52fd94f1d7e4','f938c711-3209-49df-8580-13f9c96b9fbf',NULL,'rent','Martie 2026',460,'EUR','2026-03-25 00:00:00',NULL,NULL,'RO83REVO0000188367446976','03',NULL,NULL,NULL,'paid',NULL,'2026-03-04 07:59:29'),('51e5c416-c514-4255-9900-fc11382d5d05','5ad35b8e-e254-435b-bfbc-be5f3777a2dc',NULL,'07ecbc7b-5885-40eb-b596-e34ed33adb3b','utilities','Hidroelectrica',1013.98,'RON','2026-03-09 00:00:00','2026-01-22 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26100572475','hidroelectrica','8000882523',NULL,'paid',NULL,'2026-01-23 07:15:30'),('53c955f2-ae51-4247-a567-69e06e92fdc8','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'f5ea83f7-daae-4879-aa84-100347f2ad41','ebloc','e-bloc',191.76,'RON','2026-04-19 00:00:00','2026-03-22 00:00:00','Asociatia de Proprietari Str. Spineni Nr.1','RO41UGBI0000622002421RON','FEBRUARIE 2026',NULL,'A1FA387',NULL,'paid',NULL,'2026-03-26 09:48:13'),('5919f926-3d87-4039-a2bc-d0b1949f285f','e06b83db-1331-4137-a687-3058b969ccae',NULL,'9ee5decf-b072-4c91-8187-c9acced50d6c','utilities','Vodafone',44.6,'RON','2026-03-22 00:00:00','2026-03-02 00:00:00','Vodafone Romania S.A.','RO23INGB0001000000000222','VDF773296364',NULL,'271768784',NULL,'paid',NULL,'2026-03-06 10:33:52'),('6505748b-1b13-4ada-a42e-72145953e358','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff',NULL,'rent','Martie 2026',370,'EUR','2026-03-19 00:00:00',NULL,NULL,'RO83REVO0000188367446976','03',NULL,NULL,NULL,'paid',NULL,'2026-02-25 16:50:51'),('6565967d-80f4-491f-aa45-1026bbc75648','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'other','Vodafone',44.65,'RON','2026-01-21 00:00:00',NULL,NULL,'RO23INGB0001000000000222','VDF760317168','vodafone','271768784',NULL,'paid',NULL,'2026-01-09 18:07:11'),('68348cfa-1270-46a1-a087-7f19f0102929','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,'8882643f-4def-4f8a-a6d8-f1ca49e83522','ebloc','e-bloc',574.77,'RON','2026-02-15 00:00:00','2026-01-26 00:00:00','Asociatia de Proprietari Bloc M6','RO71CECEB30834RON0330402','DECEMBRIE 2025',NULL,NULL,NULL,'paid',NULL,'2026-01-27 12:10:01'),('728b974d-a8f7-44f6-bad3-82e028e79f88','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'utilities','Hidroelectrica',155.58,'RON','2026-01-30 00:00:00',NULL,NULL,NULL,'25110944550','220e67e4-8d81-487c-8d35-639c3ac03a6b','8000324423',NULL,'paid',NULL,'2026-01-03 23:17:03'),('754b5204-67f0-4c12-a10a-a0c0f9fcbee0','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'c47db48f-d2b1-4291-8f1c-9ad096ee061f','utilities','Engie',29.67,'RON','2026-02-18 00:00:00','2026-01-19 00:00:00','ENGIE Romania S.A.','RO23RZBR0000060011419498','70900478766','engie','115335242,',NULL,'paid',NULL,'2026-01-20 18:48:37'),('7ac330e4-491a-40a0-93d2-85750ad5acff','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'07b31939-5944-4f5e-b982-5ee9e1dd1e67','utilities','Engie',29.67,'RON','2026-01-11 00:00:00',NULL,NULL,'RO23RZBR0000060011419498','70900452673 din','engie','115335242,',NULL,'paid',NULL,'2026-01-07 16:32:47'),('7ec3150d-2385-4221-8dad-981b6ca07ea8','b2c07414-e2bb-4515-b568-5f3dd596f14d','dd205ad6-b2da-413e-957b-af790c7798d8',NULL,'rent','Mai 2026',360,'EUR','2026-05-01 00:00:00',NULL,NULL,'RO83REVO0000188367446976','05',NULL,NULL,NULL,'pending',NULL,'2026-04-03 07:32:00'),('81cc2e61-29ef-4d6d-9faf-2098c89c3aae','e06b83db-1331-4137-a687-3058b969ccae','5090eafa-f0b3-46d3-804e-06bffb59f37a',NULL,'rent','Martie 2026',405,'EUR','2026-03-10 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','03',NULL,NULL,NULL,'paid',NULL,'2026-02-11 18:28:19'),('82241e5a-644d-4fe2-9584-a6050c610071','e06b83db-1331-4137-a687-3058b969ccae',NULL,'d148ae3c-0e59-40d7-b476-36fcdcb8e4ea','utilities','Hidroelectrica',77.25,'RON','2026-03-09 00:00:00','2026-01-22 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26100303568','hidroelectrica','8000324444',NULL,'paid',NULL,'2026-01-23 10:46:42'),('88a0f25e-7449-4427-a9f5-ad09def27c34','7b590e84-affd-4310-962d-d889c42ed137',NULL,'46286284-b44b-442c-bd6a-89737d3a4a6a','utilities','PPC Gaze',500.68,'RON','2026-03-11 00:00:00','2026-02-24 00:00:00','PPC Energie S.A.','RO45','49010789776',NULL,'PEYIFCERN053002',NULL,'paid',NULL,'2026-02-25 16:51:13'),('88b2dde8-3d6f-4cb6-b99e-d496d89f51f7','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'f5ea83f7-daae-4879-aa84-100347f2ad41','utilities','E-bloc',144.02,'RON','2026-01-05 00:00:00',NULL,NULL,'RO41UGBI0000622002421RON','NOIEMBRIE 2025',NULL,'A1FA387',NULL,'paid',NULL,'2026-01-05 21:18:54'),('95df5fda-7bff-4cb8-9dfd-30707eb892ac','a3b56669-a657-481c-b57f-52fd94f1d7e4','f938c711-3209-49df-8580-13f9c96b9fbf',NULL,'rent','February 2026',460,'EUR','2026-02-25 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'paid',NULL,'2026-01-27 12:09:23'),('985539d5-1c9a-46b3-bb53-3f3ffdaff8fd','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,'8ae4fd2e-7827-4652-af89-9b7f2dbd43e0','ebloc','e-bloc',1240,'RON','2026-03-07 00:00:00','2026-02-05 00:00:00','Asociatia de Proprietari Bl. 12 Titan','RO40RNCB0089003747230001','DECEMBRIE 2025',NULL,'A4F80C5',NULL,'paid',NULL,'2026-02-05 10:21:56'),('9ea781a3-c727-4730-b069-8539661fd10c','7b590e84-affd-4310-962d-d889c42ed137',NULL,NULL,'utilities','Digi',108.75,'RON','2026-01-31 00:00:00',NULL,NULL,'RO51INGB0001000000018827','14744500','digi',NULL,NULL,'paid',NULL,'2026-01-09 16:32:35'),('9f0595b9-ac1b-44ec-9a11-9e223f3438ea','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','bf153da6-17f3-4146-ba80-54fd9ece7621',NULL,'rent','Aprilie 2026',180,'EUR','2026-04-10 00:00:00',NULL,NULL,'RO83REVO0000188367446976','04',NULL,NULL,NULL,'paid',NULL,'2026-03-27 11:17:45'),('9f4ed386-8d52-4703-9cd6-9d6d5930e25a','7b590e84-affd-4310-962d-d889c42ed137',NULL,'38fc9ea3-cb4c-4ae8-8dce-239f3fcf8ddb','utilities','Hidroelectrica',1046.5,'RON','2026-03-09 00:00:00','2026-01-21 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26100143344',NULL,'8000324406',NULL,'paid',NULL,'2026-01-22 08:03:56'),('9f58656e-c5d0-4b11-9a69-982732bd7cb6','e06b83db-1331-4137-a687-3058b969ccae',NULL,'d148ae3c-0e59-40d7-b476-36fcdcb8e4ea','utilities','Hidroelectrica',78.84,'RON','2026-03-30 00:00:00','2026-02-13 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26101623965',NULL,'Cod Cont Contract: 8000324444',NULL,'paid',NULL,'2026-02-13 16:40:50'),('a0fe92f9-d952-47ba-b54e-f05023f27cf8','a3b56669-a657-481c-b57f-52fd94f1d7e4','f938c711-3209-49df-8580-13f9c96b9fbf',NULL,'rent','Aprilie 2026',460,'EUR','2026-04-25 00:00:00',NULL,NULL,'RO83REVO0000188367446976','04',NULL,NULL,NULL,'pending',NULL,'2026-03-26 09:47:47'),('a3dec734-6bdb-4ed8-9adc-fb43589eec63','a3b56669-a657-481c-b57f-52fd94f1d7e4','f938c711-3209-49df-8580-13f9c96b9fbf',NULL,'rent','January 2026',460,'EUR','2026-01-25 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','01',NULL,NULL,NULL,'paid',NULL,'2026-01-09 21:03:56'),('a55e6f38-0678-4547-8307-465633064f13','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','bf153da6-17f3-4146-ba80-54fd9ece7621',NULL,'rent','February 2026',170,'EUR','2026-02-10 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'paid',NULL,'2026-01-11 09:28:04'),('a5d2ab8d-596d-4583-a9b3-32521e4bb8ff','7b590e84-affd-4310-962d-d889c42ed137',NULL,'46286284-b44b-442c-bd6a-89737d3a4a6a','utilities','PPC Gaze',265.51,'RON','2026-01-08 00:00:00','2025-12-23 00:00:00','PPC Energie S.A.','RO45','93000445050','ppc.gaz','PEYIFCERN053002',NULL,'paid',NULL,'2026-01-12 17:42:08'),('a5e03ef7-d58a-4d53-892b-05cb5448980c','ff311a1c-9b07-42ce-9f38-f409be30e604',NULL,NULL,'rent','March 2026',1299,'RON','2026-02-04 00:00:00',NULL,NULL,NULL,NULL,NULL,NULL,NULL,'paid',NULL,'2026-02-04 15:44:45'),('a7c2068c-de0f-4f0c-bbdd-78e7cb3ceeac','e06b83db-1331-4137-a687-3058b969ccae',NULL,'afc58013-a26a-4273-9aac-d5c62dc8c37d','ebloc','e-bloc',163.54,'RON','2026-02-28 00:00:00','2026-02-11 00:00:00','Asociatia de Proprietari Aleea Mizil Nr. 57','RO86INGB0000999909534657','DECEMBRIE 2025',NULL,'A54BB6E',NULL,'paid',NULL,'2026-02-11 18:29:23'),('a82017e4-b4ea-4d6f-8917-7233cc880e00','e06b83db-1331-4137-a687-3058b969ccae','5090eafa-f0b3-46d3-804e-06bffb59f37a',NULL,'rent','Aprilie 2026',405,'EUR','2026-04-10 00:00:00',NULL,NULL,'RO83REVO0000188367446976','04',NULL,NULL,NULL,'pending',NULL,'2026-03-11 15:53:50'),('a9b58180-e7cd-40c7-8f02-57df9011dd2e','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,NULL,'utilities','e-bloc',1125,'RON','2026-02-05 00:00:00',NULL,NULL,'RO40RNCB0089003747230001','NOIEMBRIE 2025',NULL,'A4F80C5',NULL,'paid',NULL,'2026-01-06 15:04:40'),('a9dfa98c-a033-4a4d-a10d-971d2e82a7a6','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','bf153da6-17f3-4146-ba80-54fd9ece7621',NULL,'rent','January 2026',170,'EUR','2026-01-10 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','01',NULL,NULL,NULL,'paid',NULL,'2026-01-09 21:03:56'),('ac0a2a03-e25e-4f0f-b775-bd99a8135d46','7b590e84-affd-4310-962d-d889c42ed137',NULL,'dc09419b-212a-4e3d-914e-17f083911fc5','utilities','Hidroelectrica',769.46,'RON','2026-01-26 00:00:00',NULL,'SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','25110487592',NULL,'8000324406',NULL,'paid',NULL,'2026-01-09 20:33:14'),('b4100d8a-7371-42c1-a94a-4c87285ab435','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,'8882643f-4def-4f8a-a6d8-f1ca49e83522','ebloc','e-bloc',568.13,'RON','2026-03-09 00:00:00','2026-02-17 00:00:00','Asociatia de Proprietari Bloc M6','RO71CECEB30834RON0330402','IANUARIE 2026','e-bloc',NULL,'\"IANUARIE 2026\"','paid',NULL,'2026-02-21 12:19:26'),('b7bcfd92-4b91-4ff2-a259-660a2d071fa2','e06b83db-1331-4137-a687-3058b969ccae',NULL,NULL,'utilities','Engie',234.01,'RON','2026-01-19 00:00:00',NULL,NULL,'RO40RZBR0000060010660361','11803290532',NULL,'4001941859',NULL,'paid',NULL,'2026-01-05 17:25:04'),('b8b619d3-f938-467a-b286-86afa305fe65','5ad35b8e-e254-435b-bfbc-be5f3777a2dc',NULL,'07ecbc7b-5885-40eb-b596-e34ed33adb3b','utilities','Hidroelectrica',829.41,'RON','2026-04-27 00:00:00','2026-03-12 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26102873464',NULL,'Cod Cont Contract: 8000882523',NULL,'pending',NULL,'2026-03-12 18:38:09'),('b9898d7f-4a38-420e-a2ab-a1d934703e91','e06b83db-1331-4137-a687-3058b969ccae','5090eafa-f0b3-46d3-804e-06bffb59f37a',NULL,'rent','February 2026',405,'EUR','2026-02-10 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','02',NULL,NULL,NULL,'paid',NULL,'2026-01-09 18:34:54'),('bb5ba5af-6ccd-4ba3-b099-6ad0f9085040','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'c47db48f-d2b1-4291-8f1c-9ad096ee061f','utilities','Engie',30.41,'RON','2026-04-15 00:00:00','2026-03-12 00:00:00','ENGIE Romania S.A.','RO23RZBR0000060011419498','70900512199',NULL,'115335242,',NULL,'paid',NULL,'2026-03-12 18:19:35'),('bc6226a8-f88c-4d69-93e7-3cf7c565771e','7b590e84-affd-4310-962d-d889c42ed137',NULL,'46286284-b44b-442c-bd6a-89737d3a4a6a','utilities','PPC Gaze',390.56,'RON','2026-04-09 00:00:00','2026-03-25 00:00:00','PPC Energie S.A.','RO45','20013251623',NULL,'PEYIFCERN053002',NULL,'paid',NULL,'2026-03-26 09:48:13'),('be7b7a8e-61a2-48d0-9d73-29312055ea31','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'f5ea83f7-daae-4879-aa84-100347f2ad41','ebloc','e-bloc',85.74,'RON','2026-03-17 00:00:00','2026-02-17 00:00:00','Asociatia de Proprietari Str. Spineni Nr.1','RO41UGBI0000622002421RON','IANUARIE 2026',NULL,'A1FA387',NULL,'paid',NULL,'2026-02-20 12:39:48'),('c7d93cab-dea8-4e5a-9495-fd3043d97e3b','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'f5ea83f7-daae-4879-aa84-100347f2ad41','ebloc','e-bloc',152.5,'RON','2026-02-11 00:00:00','2026-01-14 00:00:00','sociatia de Proprietari Str. Spineni Nr.1','RO41UGBI0000622002421RON','DECEMBRIE 2025',NULL,'A1FA387',NULL,'paid',NULL,'2026-01-18 15:06:47'),('c7e1a379-2ea4-4516-b128-a64ce058a8bb','7b590e84-affd-4310-962d-d889c42ed137',NULL,'38fc9ea3-cb4c-4ae8-8dce-239f3fcf8ddb','utilities','Hidroelectrica',949.85,'RON','2026-04-24 00:00:00','2026-03-10 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26102325655',NULL,'Cod Cont Contract: 8000324406',NULL,'pending',NULL,'2026-03-11 15:54:12'),('c9ba0954-6e61-474c-870c-06c907e50f5a','7b590e84-affd-4310-962d-d889c42ed137',NULL,'46286284-b44b-442c-bd6a-89737d3a4a6a','utilities','PPC Gaze',38.1,'RON','2026-02-20 00:00:00','2026-02-05 00:00:00','PPC Energie S.A.','RO45','91000491154',NULL,'PEYIFCERN053002',NULL,'paid',NULL,'2026-02-06 09:53:41'),('cc0adb36-346b-4f19-99d7-aa5441d561fd','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,'9e39ce60-a853-4947-8d45-db94aa965042','utilities','Hidroelectrica',143.23,'RON','2026-03-30 00:00:00','2026-02-13 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26101677349',NULL,'Cod Cont Contract: 8000970939',NULL,'paid',NULL,'2026-02-13 16:40:50'),('d0d5fd02-9b37-45b2-8511-b5fb822c7287','5ad35b8e-e254-435b-bfbc-be5f3777a2dc',NULL,'07ecbc7b-5885-40eb-b596-e34ed33adb3b','utilities','Hidroelectrica',1108.08,'RON','2026-03-30 00:00:00','2026-02-13 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26101684954',NULL,'Cod Cont Contract: 8000882523',NULL,'paid',NULL,'2026-02-13 16:08:31'),('d2c3cdb8-229b-40aa-a74a-933cdd444c7c','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'telecom','Telekom',31.5,'RON','2026-03-02 00:00:00','2026-02-16 00:00:00','TELEKOM ROMANIA MOBILE COMMUNICATIONS SA',NULL,'260101089192','telekom','99170010871410',NULL,'paid',NULL,'2026-03-12 19:46:03'),('d870a1ec-06b5-466f-9a9c-f6ca22e9d458','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'491e0ee8-7c77-49bb-82da-0540381dc2fe','utilities','Engie Gaze',172.12,'RON','2026-01-22 00:00:00','2025-12-23 00:00:00','ENGIE Romania S.A. Sediul social: B-dul Mărăşeşti nr. 4 -6, sector 4,','RO40RZBR0000060010660361','11117929360','engie.gaz','4001585793',NULL,'paid',NULL,'2026-01-10 21:02:23'),('dae4022f-87aa-406e-ab27-270f94e6d8a4','e06b83db-1331-4137-a687-3058b969ccae',NULL,'afc58013-a26a-4273-9aac-d5c62dc8c37d','ebloc','e-bloc',151.43,'RON','2026-03-31 00:00:00','2026-03-05 00:00:00','Asociatia de Proprietari Aleea Mizil Nr. 57','RO86INGB0000999909534657','IANUARIE 2026',NULL,'A54BB6E',NULL,'paid',NULL,'2026-03-05 17:45:42'),('e8883020-9209-4cf5-8c01-cc924fa499f8','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff',NULL,'rent','January 2026',360,'EUR','2026-01-20 00:00:00',NULL,NULL,'RO95RZBR0000060014291924','01',NULL,NULL,NULL,'paid',NULL,'2026-01-09 21:03:56'),('ee8a998b-18f8-47d1-a8ec-d65619995dda','b2c07414-e2bb-4515-b568-5f3dd596f14d',NULL,'c47db48f-d2b1-4291-8f1c-9ad096ee061f','utilities','Engie',270.57,'RON','2026-03-16 00:00:00','2026-02-12 00:00:00','ENGIE Romania S.A.','RO23RZBR0000060011419498','70400821019',NULL,'115335242,',NULL,'paid',NULL,'2026-02-15 19:24:53'),('efb895a4-7601-41ff-abf3-ba4ab71181be','7b590e84-affd-4310-962d-d889c42ed137',NULL,'78ef93bb-4dad-43fe-9e32-75472b4ec672','utilities','Digi',131.67,'RON','2026-02-28 00:00:00','2026-02-06 00:00:00','Digi Romania S.A.','RO51INGB0001000000018827','21681507','digi',NULL,NULL,'paid',NULL,'2026-02-06 10:27:23'),('f43f3b36-21b4-465f-b8e4-71f8cc0f84a7','e06b83db-1331-4137-a687-3058b969ccae',NULL,'08cea347-a648-4bd3-8be7-c696410e63ab','utilities','Engie Gaze',130.35,'RON','2026-04-20 00:00:00','2026-03-19 00:00:00','ENGIE Romania S.A. Sediul social: B-dul Mărăşeşti nr. 4 -6, sector 4,','RO40RZBR0000060010660361','10619598049',NULL,'4001941859',NULL,'paid',NULL,'2026-03-21 17:06:14'),('fcc2f55f-8c85-457b-b70b-c94f6b24e04a','5ad35b8e-e254-435b-bfbc-be5f3777a2dc',NULL,'d7a6bc07-5888-412f-9120-618f1dee1766','utilities','Digi',30.5,'RON','2026-02-28 00:00:00','2026-02-06 00:00:00','Digi Romania S.A.','RO51INGB0001000000018827','21680855','digi',NULL,NULL,'paid',NULL,'2026-02-06 10:27:11'),('fde3a621-c844-4cf0-bf10-4c8064c00c89','a3b56669-a657-481c-b57f-52fd94f1d7e4',NULL,NULL,'telecom','Telekom',45.83,'RON','2025-12-30 00:00:00','2025-12-16 00:00:00','TELEKOM ROMANIA MOBILE COMMUNICATIONS SA',NULL,'250108897932','telekom','99170010871410',NULL,'paid',NULL,'2026-01-12 18:34:26'),('fe50c97c-703a-490b-85ba-14a976792405','1305a3b8-2509-4cf4-a93a-fe9a868de4c6',NULL,'9e39ce60-a853-4947-8d45-db94aa965042','utilities','Hidroelectrica',141.65,'RON','2026-03-09 00:00:00','2026-01-22 00:00:00','SPEEH HIDROELECTRICA SA','RO63RNCB0072018331870495','26100588699',NULL,'8000970939',NULL,'paid',NULL,'2026-01-23 07:04:39');
/*!40000 ALTER TABLE `bills` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `payment_notifications`
--

DROP TABLE IF EXISTS `payment_notifications`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `payment_notifications` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `bill_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `renter_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `landlord_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `amount` float NOT NULL,
  `currency` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'RON',
  `status` enum('pending','confirmed','rejected') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'pending',
  `renter_note` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Optional note from renter about the payment',
  `landlord_note` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'Optional note from landlord when confirming/rejecting',
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `confirmed_at` datetime DEFAULT NULL COMMENT 'When landlord confirmed or rejected',
  `amount_in_bill_currency` double DEFAULT NULL,
  `bill_currency` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci,
  PRIMARY KEY (`id`),
  KEY `idx_pn_bill` (`bill_id`),
  KEY `idx_pn_renter` (`renter_id`),
  KEY `idx_pn_landlord` (`landlord_id`),
  KEY `idx_pn_status` (`status`),
  KEY `idx_pn_created` (`created_at`),
  KEY `idx_pn_landlord_status` (`landlord_id`,`status`),
  CONSTRAINT `payment_notifications_ibfk_1` FOREIGN KEY (`bill_id`) REFERENCES `bills` (`id`) ON DELETE CASCADE,
  CONSTRAINT `payment_notifications_ibfk_2` FOREIGN KEY (`renter_id`) REFERENCES `renters` (`id`) ON DELETE CASCADE,
  CONSTRAINT `payment_notifications_ibfk_3` FOREIGN KEY (`landlord_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `payment_notifications`
--

LOCK TABLES `payment_notifications` WRITE;
/*!40000 ALTER TABLE `payment_notifications` DISABLE KEYS */;
INSERT INTO `payment_notifications` VALUES ('3f00ef91-38ef-4026-9b01-67dda154a138','00945337-fbbb-4c5b-b0a3-2697c1d78b60','dd205ad6-b2da-413e-957b-af790c7798d8','57ca9597-6a30-4775-bc89-71243d828a98',152.01,'RON','confirmed',NULL,NULL,'2026-03-25 08:42:06','2026-03-25 08:50:02',152.01,'RON'),('42f084d6-fd0e-403b-8362-7b4430c77cf1','364e5c7d-41d9-4742-a3fd-05c2c2c0d2e6','dd205ad6-b2da-413e-957b-af790c7798d8','57ca9597-6a30-4775-bc89-71243d828a98',360,'EUR','confirmed',NULL,NULL,'2026-04-01 09:21:27','2026-04-01 10:24:15',360,'EUR'),('4dcbf889-e0b1-4585-b18b-33daa524badf','bb5ba5af-6ccd-4ba3-b099-6ad0f9085040','dd205ad6-b2da-413e-957b-af790c7798d8','57ca9597-6a30-4775-bc89-71243d828a98',30.41,'RON','confirmed',NULL,NULL,'2026-03-12 18:25:22','2026-03-12 19:23:35',30.41,'RON'),('8e47f723-04f2-4b64-a70f-0bd7089bf87d','be7b7a8e-61a2-48d0-9d73-29312055ea31','dd205ad6-b2da-413e-957b-af790c7798d8','57ca9597-6a30-4775-bc89-71243d828a98',85.74,'RON','confirmed',NULL,NULL,'2026-02-21 09:19:10','2026-03-12 18:18:20',85.74,'RON'),('cb23e064-3d56-411c-a6b7-8c7d5d8206e4','2b38f067-b449-4bef-b5a7-3c3a37d665d3','dd205ad6-b2da-413e-957b-af790c7798d8','57ca9597-6a30-4775-bc89-71243d828a98',1836,'RON','confirmed',NULL,NULL,'2026-03-01 17:08:24','2026-03-04 07:35:33',360,'EUR'),('da0f3b26-e85f-41b7-a24c-4c61e3d4a2bb','53c955f2-ae51-4247-a567-69e06e92fdc8','dd205ad6-b2da-413e-957b-af790c7798d8','57ca9597-6a30-4775-bc89-71243d828a98',191.76,'RON','confirmed',NULL,NULL,'2026-03-26 10:46:40','2026-03-26 11:38:14',191.76,'RON');
/*!40000 ALTER TABLE `payment_notifications` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `properties`
--

DROP TABLE IF EXISTS `properties`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `properties` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `landlord_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `address` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
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
INSERT INTO `properties` VALUES ('1305a3b8-2509-4cf4-a93a-fe9a868de4c6','57ca9597-6a30-4775-bc89-71243d828a98','Str. Plutonier Radu Gheorghe Sc: A Ap: 25','Str. Plutonier Radu Gheorghe','2025-12-31 11:20:21'),('5ad35b8e-e254-435b-bfbc-be5f3777a2dc','57ca9597-6a30-4775-bc89-71243d828a98','1 Decembrie Nr 17','Loc Joaca','2026-01-08 11:51:35'),('7b590e84-affd-4310-962d-d889c42ed137','57ca9597-6a30-4775-bc89-71243d828a98','Vlad Tepes 97, Tanganu Ilfov','Vlad Tepes 97','2025-12-31 15:27:03'),('829f0dc3-f009-42a5-b488-4e257b7a6626','68459987-46aa-45b3-9344-919321993eda','home','test ','2026-01-17 20:58:45'),('a3b56669-a657-481c-b57f-52fd94f1d7e4','57ca9597-6a30-4775-bc89-71243d828a98','Strada Trapezului nr.2 Bl: M6 Sc: 2 Ap: 53','Strada Trapezului nr.2','2025-12-31 11:20:21'),('b2c07414-e2bb-4515-b568-5f3dd596f14d','57ca9597-6a30-4775-bc89-71243d828a98','Spineni nr.1, sector 4,Bucuresti Sc: A Ap: 5','Spineni nr.1, sector 4,Bucuresti','2025-12-31 11:20:21'),('e06b83db-1331-4137-a687-3058b969ccae','57ca9597-6a30-4775-bc89-71243d828a98','Str. Mizil nr.57 Sc: C2/1 Ap: 8','Str. Mizil nr.57','2025-12-31 11:20:21'),('ff311a1c-9b07-42ce-9f38-f409be30e604','b53b12de-5bc6-4016-95b6-692d3df8fe29','carpemi;io','ap carpenului','2026-02-04 15:44:19');
/*!40000 ALTER TABLE `properties` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `property_suppliers`
--

DROP TABLE IF EXISTS `property_suppliers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `property_suppliers` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `property_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `supplier_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `extraction_pattern_supplier` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `contract_id` varchar(100) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
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
INSERT INTO `property_suppliers` VALUES ('07ecbc7b-5885-40eb-b596-e34ed33adb3b','5ad35b8e-e254-435b-bfbc-be5f3777a2dc','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'Cod Cont Contract: 8000882523',1,'2026-01-08 11:52:16','2026-02-13 16:08:31'),('08cea347-a648-4bd3-8be7-c696410e63ab','e06b83db-1331-4137-a687-3058b969ccae','5f923979-987f-4bb8-838b-786ee4e275ee',NULL,'4001941859',1,'2026-01-02 13:30:12','2026-02-25 17:11:36'),('38fc9ea3-cb4c-4ae8-8dce-239f3fcf8ddb','7b590e84-affd-4310-962d-d889c42ed137','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'Cod Cont Contract: 8000324406',1,'2025-12-31 16:01:21','2026-03-11 15:54:12'),('3a68da95-4bf8-4fb9-bd79-91385e9f8b2d','829f0dc3-f009-42a5-b488-4e257b7a6626','07b31939-5944-4f5e-b982-5ee9e1dd1e67',NULL,NULL,0,'2026-01-17 21:02:24','2026-01-17 23:02:24'),('46286284-b44b-442c-bd6a-89737d3a4a6a','7b590e84-affd-4310-962d-d889c42ed137','0','PPC Energie S.A.','PEYIFCERN053002',1,'2026-01-10 13:55:47','2026-01-11 15:45:20'),('491e0ee8-7c77-49bb-82da-0540381dc2fe','b2c07414-e2bb-4515-b568-5f3dd596f14d','5f923979-987f-4bb8-838b-786ee4e275ee',NULL,'4001585793',1,'2026-01-05 15:24:35','2026-01-05 15:24:35'),('669c2977-e40d-48ba-b4e4-db35723e311a','a3b56669-a657-481c-b57f-52fd94f1d7e4','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'Cod Cont Contract: 8000324423',1,'2025-12-31 15:31:52','2026-02-13 16:40:50'),('6df0773b-4127-44d9-be4e-2045d6365633','a3b56669-a657-481c-b57f-52fd94f1d7e4','ee8a274b-837f-4d72-860e-5aad97487958',NULL,NULL,1,'2026-01-02 09:22:42','2026-01-02 09:22:42'),('78ef93bb-4dad-43fe-9e32-75472b4ec672','7b590e84-affd-4310-962d-d889c42ed137','ee8a274b-837f-4d72-860e-5aad97487958',NULL,NULL,1,'2026-01-02 09:43:44','2026-01-02 09:43:44'),('7d5fa30c-a9ce-4403-9902-6dd3e777e644','829f0dc3-f009-42a5-b488-4e257b7a6626','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,NULL,0,'2026-01-17 21:02:21','2026-01-17 23:02:21'),('8882643f-4def-4f8a-a6d8-f1ca49e83522','a3b56669-a657-481c-b57f-52fd94f1d7e4','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,NULL,1,'2026-01-03 20:45:54','2026-01-19 19:18:27'),('8ae4fd2e-7827-4652-af89-9b7f2dbd43e0','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,'A4F80C5',1,'2025-12-31 11:20:21','2026-02-25 17:11:58'),('9a51e17a-0b57-471c-9bfa-f38683575962','4351d460-63ae-4e9a-9bc7-65b792d77718','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,NULL,0,'2026-01-03 16:35:26','2026-01-03 16:35:26'),('9e39ce60-a853-4947-8d45-db94aa965042','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'Cod Cont Contract: 8000970939',1,'2025-12-31 15:29:29','2026-02-25 17:11:58'),('9edd0df1-2b09-4556-a8a0-a84ca8791d4b','829f0dc3-f009-42a5-b488-4e257b7a6626','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,NULL,0,'2026-01-17 21:02:27','2026-01-17 23:02:27'),('9ee5decf-b072-4c91-8187-c9acced50d6c','e06b83db-1331-4137-a687-3058b969ccae','00ca9f3c-93a9-40b0-940d-416739d12d6e',NULL,'271768784',1,'2026-01-02 09:09:47','2026-02-06 09:53:41'),('afc58013-a26a-4273-9aac-d5c62dc8c37d','e06b83db-1331-4137-a687-3058b969ccae','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,'A54BB6E',1,'2026-01-03 20:46:07','2026-02-25 17:11:35'),('c0d5105c-f126-4a3a-b6c9-73c35e9cddb1','829f0dc3-f009-42a5-b488-4e257b7a6626','91a20e9c-ca6a-4a27-91f5-51cae6e1903f',NULL,NULL,0,'2026-01-17 21:02:31','2026-01-17 23:02:31'),('c47db48f-d2b1-4291-8f1c-9ad096ee061f','b2c07414-e2bb-4515-b568-5f3dd596f14d','07b31939-5944-4f5e-b982-5ee9e1dd1e67',NULL,'115335242,',1,'2026-01-05 17:59:40','2026-01-05 17:59:51'),('c9a7751d-04eb-4c86-8706-394742535d0d','829f0dc3-f009-42a5-b488-4e257b7a6626','f9363812-3e73-4edb-b26f-af721cfdefc6',NULL,NULL,0,'2026-01-17 21:02:34','2026-01-17 23:02:34'),('d148ae3c-0e59-40d7-b476-36fcdcb8e4ea','e06b83db-1331-4137-a687-3058b969ccae','dc09419b-212a-4e3d-914e-17f083911fc5',NULL,'Cod Cont Contract: 8000324444',1,'2025-12-31 15:35:58','2026-02-25 17:11:37'),('d7a6bc07-5888-412f-9120-618f1dee1766','5ad35b8e-e254-435b-bfbc-be5f3777a2dc','ee8a274b-837f-4d72-860e-5aad97487958',NULL,NULL,1,'2026-01-08 11:51:52','2026-01-08 13:51:52'),('f5ea83f7-daae-4879-aa84-100347f2ad41','b2c07414-e2bb-4515-b568-5f3dd596f14d','1e0537e9-4242-4e5e-82e2-6fad9e08494f',NULL,'A1FA387',1,'2026-01-03 20:06:21','2026-02-25 17:11:13');
/*!40000 ALTER TABLE `property_suppliers` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `renters`
--

DROP TABLE IF EXISTS `renters`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `renters` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `property_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `phone` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `rent_day` int DEFAULT NULL,
  `start_contract_date` date DEFAULT NULL,
  `rent_amount` float DEFAULT NULL,
  `rent_currency` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'EUR',
  `access_token` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  `password_hash` varchar(255) COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `language` varchar(10) COLLATE utf8mb4_unicode_ci DEFAULT 'ro',
  `email_notifications` tinyint(1) DEFAULT '0',
  PRIMARY KEY (`id`),
  UNIQUE KEY `access_token` (`access_token`),
  KEY `idx_renters_property` (`property_id`),
  KEY `idx_renters_token` (`access_token`),
  KEY `idx_renters_email` (`email`),
  KEY `idx_renters_email_login` (`email`),
  CONSTRAINT `renters_ibfk_1` FOREIGN KEY (`property_id`) REFERENCES `properties` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `renters`
--

LOCK TABLES `renters` WRITE;
/*!40000 ALTER TABLE `renters` DISABLE KEYS */;
INSERT INTO `renters` VALUES ('5090eafa-f0b3-46d3-804e-06bffb59f37a','e06b83db-1331-4137-a687-3058b969ccae','Miruna Pricopie',NULL,'+40763565340',10,'2025-08-25',405,'EUR','aeb52050-a314-467f-a77c-65e91abb3102','2026-01-01 19:57:56',NULL,'ro',0),('8d9225f3-9d5d-4961-b6e4-2cbb0a4a16ff','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','Zohaib','pio.doi@gmail.com','+923365264425',20,'2026-03-17',370,'EUR','74a4a9ad-5b98-4649-8372-c7ff767c5f4f','2026-01-01 20:29:29','$2b$12$O5OYvzSsFHuA8L6YIrcfoe/ACm.uCfjNcaXwEyGIkzhMaeuzavg2q','ro',0),('bf153da6-17f3-4146-ba80-54fd9ece7621','1305a3b8-2509-4cf4-a93a-fe9a868de4c6','Sojib',NULL,'+40 731 470 195',10,'2025-03-19',180,'EUR','24e267fd-e913-4049-ae10-ecb3b75b3251','2026-01-01 20:30:45',NULL,'ro',0),('dd205ad6-b2da-413e-957b-af790c7798d8','b2c07414-e2bb-4515-b568-5f3dd596f14d','Andrei Zdrali',NULL,'+40731733991',1,'2025-09-01',360,'EUR','e49c06f9-85fb-44dc-9bb8-63b57aa6ba70','2026-01-01 19:53:33',NULL,'ro',0),('f938c711-3209-49df-8580-13f9c96b9fbf','a3b56669-a657-481c-b57f-52fd94f1d7e4','Hraniceru Viorel',NULL,'+40736739166',25,'2025-10-20',460,'EUR','f725a9cf-cbd6-403a-844a-43a7a1c9d044','2026-01-01 19:23:17',NULL,'ro',0);
/*!40000 ALTER TABLE `renters` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `suppliers`
--

DROP TABLE IF EXISTS `suppliers`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `suppliers` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `has_api` tinyint(1) DEFAULT '0',
  `bill_type` enum('rent','utilities','telecom','ebloc','other') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'utilities',
  `extraction_pattern_supplier` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
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

--
-- Table structure for table `user_preferences`
--

DROP TABLE IF EXISTS `user_preferences`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `user_preferences` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `user_id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `language` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'en',
  `view_mode` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'list',
  `rent_warning_days` int DEFAULT '5',
  `rent_currency` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'EUR',
  `bill_currency` varchar(10) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'RON',
  `date_format` varchar(20) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT 'DD/MM/YYYY',
  `phone_number` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `landlord_name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `personal_email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iban` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `updated_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP,
  `property_order` text CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci COMMENT 'JSON array of property IDs for display order preference',
  `iban_eur` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `iban_usd` varchar(50) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  PRIMARY KEY (`id`),
  UNIQUE KEY `user_id` (`user_id`),
  KEY `idx_prefs_user` (`user_id`),
  CONSTRAINT `user_preferences_ibfk_1` FOREIGN KEY (`user_id`) REFERENCES `users` (`id`) ON DELETE CASCADE
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `user_preferences`
--

LOCK TABLES `user_preferences` WRITE;
/*!40000 ALTER TABLE `user_preferences` DISABLE KEYS */;
INSERT INTO `user_preferences` VALUES ('1e6d715a-db7f-4207-954e-d32416bb5e2d','b53b12de-5bc6-4016-95b6-692d3df8fe29','en','list',5,'EUR','RON','DD/MM/YYYY',NULL,NULL,'harabordan@gmail.com',NULL,'2026-02-04 15:43:17',NULL,NULL,NULL),('3ee16f6c-f332-42a5-836c-461fecea6ad5','68459987-46aa-45b3-9344-919321993eda','en','list',5,'EUR','RON','DD/MM/YYYY',NULL,NULL,'piodoi+pp@gmail.com',NULL,'2026-02-03 17:10:11',NULL,NULL,NULL),('c3c863d5-b123-41bb-aa97-0ef8afd42828','57ca9597-6a30-4775-bc89-71243d828a98','ro','grid',5,'EUR','RON','DD/MM/YYYY','+40742755724','Ionut Poclitaru','pio.doi@gmail.com','RO83REVO0000188367446976','2026-02-15 19:52:57','[\"1305a3b8-2509-4cf4-a93a-fe9a868de4c6\", \"a3b56669-a657-481c-b57f-52fd94f1d7e4\", \"b2c07414-e2bb-4515-b568-5f3dd596f14d\", \"e06b83db-1331-4137-a687-3058b969ccae\", \"5ad35b8e-e254-435b-bfbc-be5f3777a2dc\", \"7b590e84-affd-4310-962d-d889c42ed137\"]','RO83REVO0000188367446976',NULL);
/*!40000 ALTER TABLE `user_preferences` ENABLE KEYS */;
UNLOCK TABLES;

--
-- Table structure for table `users`
--

DROP TABLE IF EXISTS `users`;
/*!40101 SET @saved_cs_client     = @@character_set_client */;
/*!50503 SET character_set_client = utf8mb4 */;
CREATE TABLE `users` (
  `id` varchar(36) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `email` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `name` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL,
  `role` enum('admin','landlord') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci NOT NULL DEFAULT 'landlord',
  `password_hash` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `oauth_provider` enum('google','facebook') CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `oauth_id` varchar(255) CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci DEFAULT NULL,
  `subscription_tier` int DEFAULT '0',
  `subscription_expires` datetime DEFAULT NULL,
  `created_at` datetime NOT NULL DEFAULT CURRENT_TIMESTAMP,
  PRIMARY KEY (`id`),
  UNIQUE KEY `email` (`email`),
  KEY `idx_users_email` (`email`),
  KEY `idx_users_role` (`role`),
  KEY `idx_users_oauth` (`oauth_provider`,`oauth_id`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
/*!40101 SET character_set_client = @saved_cs_client */;

--
-- Dumping data for table `users`
--

LOCK TABLES `users` WRITE;
/*!40000 ALTER TABLE `users` DISABLE KEYS */;
INSERT INTO `users` VALUES ('57ca9597-6a30-4775-bc89-71243d828a98','pio.doi@gmail.com','PioLand','admin','$2b$12$fPhRbMZJ2ypYpVGt/AAGNuyGXdx089aq8P20hGOvnCk5lGDxj3ENC',NULL,NULL,7,NULL,'2025-12-31 11:13:57'),('68459987-46aa-45b3-9344-919321993eda','piodoi+pp@gmail.com','NoLand','landlord','$2b$12$Ngwc3T6mfF5861YS1SZtMu3ozBHo2oXLwMTFOHKt66B25Jcesy8gK',NULL,NULL,0,NULL,'2026-01-17 20:57:31'),('b53b12de-5bc6-4016-95b6-692d3df8fe29','harabordan@gmail.com','Dan','landlord',NULL,'google','103433939012715468068',0,NULL,'2026-02-04 15:43:17');
/*!40000 ALTER TABLE `users` ENABLE KEYS */;
UNLOCK TABLES;
/*!40103 SET TIME_ZONE=@OLD_TIME_ZONE */;

/*!40101 SET SQL_MODE=@OLD_SQL_MODE */;
/*!40014 SET FOREIGN_KEY_CHECKS=@OLD_FOREIGN_KEY_CHECKS */;
/*!40014 SET UNIQUE_CHECKS=@OLD_UNIQUE_CHECKS */;
/*!40101 SET CHARACTER_SET_CLIENT=@OLD_CHARACTER_SET_CLIENT */;
/*!40101 SET CHARACTER_SET_RESULTS=@OLD_CHARACTER_SET_RESULTS */;
/*!40101 SET COLLATION_CONNECTION=@OLD_COLLATION_CONNECTION */;
/*!40111 SET SQL_NOTES=@OLD_SQL_NOTES */;

-- Dump completed on 2026-04-10 11:23:46
