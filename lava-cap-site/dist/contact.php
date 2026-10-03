<?php
// Simple contact handler for Hostinger shared hosting. Set $to, then test once after upload.
$to = 'admin@lavacapmine.com';
if ($_SERVER['REQUEST_METHOD'] !== 'POST' || !empty($_POST['website'])) { header('Location: index.html'); exit; }
$name = trim(strip_tags($_POST['name'] ?? ''));
$email = filter_var($_POST['email'] ?? '', FILTER_VALIDATE_EMAIL);
$reason = trim(strip_tags($_POST['reason'] ?? ''));
$msg = trim(strip_tags($_POST['message'] ?? ''));
if (!$name || !$email || !$msg) { http_response_code(400); echo 'Please go back and fill in every field.'; exit; }
$subject = 'Website message: ' . preg_replace('/[\r\n]+/', ' ', $reason);
$body = "Name: $name\nEmail: $email\nTopic: $reason\n\n$msg\n";
$headers = "From: no-reply@lavacapmine.com\r\nReply-To: $email\r\n";
@mail($to, $subject, $body, $headers);
header('Location: thanks.html');
