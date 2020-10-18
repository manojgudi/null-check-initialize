$getJkk = Npp::find()->where(['id' => $getNpp['npp']])->asArray()->one();
$jkk_config = $getJkk['jkk'];
