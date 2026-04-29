# 업무보고 자동화 - 작업 스케줄러 등록
# 관리자 권한으로 실행하세요

schtasks /create /tn "DailyReport" /tr "C:\Yuna\daily.bat" /sc WEEKLY /d MON,TUE,WED,THU,FRI /st 17:40 /rl HIGHEST /f

if ($LASTEXITCODE -eq 0) {
    Write-Host "일일 업무보고 등록 완료 (평일 17:40)" -ForegroundColor Green
} else {
    Write-Host "일일 업무보고 등록 실패" -ForegroundColor Red
}

schtasks /create /tn "WeeklyReport" /tr "C:\Yuna\weekly.bat" /sc WEEKLY /d FRI /st 09:30 /rl HIGHEST /f

if ($LASTEXITCODE -eq 0) {
    Write-Host "주간 업무보고 등록 완료 (금요일 09:30)" -ForegroundColor Green
} else {
    Write-Host "주간 업무보고 등록 실패" -ForegroundColor Red
}
