data "aws_ami" "windows-sql-server" {
  most_recent = true
  filter {
    name   = "name"
    values = ["Windows_Server-2022-English-Full-SQL_2022_Standard*"]
  }
  filter {
    name   = "virtualization-type"
    values = ["hvm"]
  }
  owners = ["801119661308"] # Amazon
}
