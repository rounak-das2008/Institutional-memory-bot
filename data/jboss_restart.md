# Restarting JBoss - Example Runbook (v1)
Steps V1:
1. SSH to gateway01 VM
2. Change user to test2
3. As test2 run /etc/standalone.sh

# Restarting JBoss - Updated (v2)
Steps V2:
1. SSH to gateway02 VM
2. Change user to test3
3. Clear /home/test3/*.log files
4. Run /etc/jbossas/standalone.sh

# JBoss Troubleshooting

## Common Issues
- **Port conflicts**: Check if port 8080 is already in use
- **Memory issues**: Increase heap size in standalone.conf
- **Permission errors**: Ensure proper file permissions for JBoss user

## Log Locations
- Application logs: `/var/log/jboss/`
- Server logs: `/opt/jboss/standalone/log/`
- System logs: `/var/log/messages`

## Health Check
To verify JBoss is running properly:
1. Check process: `ps aux | grep jboss`
2. Test connectivity: `curl http://localhost:8080`
3. Review logs for errors: `tail -f /var/log/jboss/server.log`
