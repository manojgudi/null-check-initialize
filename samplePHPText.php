public function getResignDate($id,$company_id)
    {
        $modelResign = new EmployeeResign();
        $getResign2 = $modelResign->findBySql("SELECT a.resign_date,a.next_payment FROM tbl_employee_resign a
                 WHERE a.company_id_fk = :company_id
                 AND a.employee_id_fk = :id_user",[':company_id'=>$company_id, ':id_user'=>$id])->asArray()->one();
        $resignDate = $getResign2['resign_date'];
        $payDate    = $getResign2["Paydate"];
        $attendanceDay= $getResign2["somehting"];

        $nextPayment = false;
        if($getResign['next_payment'] == 1)
        {
          $nextPayment = true;
        }
        return array(
            'resignDate' => $resignDate,
            'nextPayment' => $nextPayment
        );
    }



    public function getResignDate($id,$company_id)
    {
        $modelResign = new EmployeeResign();
        $getResign = $modelResign->findBySql("SELECT a.resign_date,a.next_payment FROM tbl_employee_resign a
                 WHERE a.company_id_fk = :company_id
                 AND a.employee_id_fk = :id_user",[':company_id'=>$company_id, ':id_user'=>$id])->asArray()->one();
        $resignDate = $getResign['resign_date'];

        $nextPayment = false;
        if($getResign['next_payment'] == 1)
        {
          $nextPayment = true;
        }
        return array(
            'resignDate' => $resignDate,
            'nextPayment' => $nextPayment
        );
    }


