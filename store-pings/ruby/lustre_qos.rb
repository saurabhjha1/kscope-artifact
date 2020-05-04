#!/u/staff/aparga/.rbenv/versions/2.0.0-p247/bin/ruby
#require 'pry'
require 'timeout'
require 'optparse'
require 'thread'
require 'logger'
require 'fileutils'

$LFS="/opt/cray/lustre-cray_gem_s/default/bin/lfs"

$options ={}
$options[:directory] = "/scratch/staff/<user>/testdir"
$options[:timeout] = 30
$options[:threads] = 16
$options[:create] = false


$hostname=`hostname`.strip

optparse = OptionParser.new do |opts|
  opts.on( '-h', '--help', 'Display this screen.') do
    puts opts
    exit
  end
  opts.on( '-d', '--dir Directory', 'Directory to test on ') do |dir|
    $options[:directory] = dir
  end
  opts.on( '-c', '--create', 'Create files') do |create|
    $options[:create] = true
  end
end
optparse.parse!

$options[:directory] << '/' << $hostname
$log=Logger.new(STDOUT)

$log.formatter = proc do |severity, datetime, progname, msg|
  "#{msg}\n"
end

class StackingError < StandardError
end

class TEST
  def initialize(directory)
    @target_dir=directory
    @cmds={"create_file"=>1,"write"=>2}
    @timeout=$options[:timeout]
    @threads=$options[:threads]
    lfs_osts=String.new
    begin
      self.create_dir
      Timeout::timeout(@timeout){lfs_osts=`#{$LFS} osts #{@target_dir}| tail -1`}
      if $?.exitstatus != 0 then
        raise SystemCallError
      end
    rescue Timeout::Error
      self.write_line(0,@target_dir,nil,nil,1)
      exit
    rescue
      self.write_line(0,@target_dir,nil,nil,2)
      exit
    end
    @max_ost=lfs_osts.split(":")[0].to_i
    @snx_name=lfs_osts.split(":")[1].split("-")[0].strip
    self.write_line(0,@snx_name,nil,nil,0)
  end

  def write_line(what,where,target,perf,ec)
    t=Time.now.to_i
    $log.info "#{$hostname},#{t},#{what},#{where},#{target},#{perf},#{ec}"
  end

  def para_cmd_osts(cmd)
      jobs=[]
      r=0
      @threads.times do |i|
        jobs[i]=Thread.new do
          (i..@max_ost).step(@threads).each do |ost|
            Thread.current[:ost]=ost
            begin
              ra=[]
              Timeout::timeout(@timeout){
                Thread.handle_interrupt(TimeoutError => :on_blocking) {
                  r=self.send(cmd,ost)}}
              if r !=0 then
                raise SystemCallError
              end
            rescue Timeout::Error
              write_line(@cmds[cmd],@snx_name,ost,nil,1)
            rescue =>e
              puts e
              puts e.backtrace
              write_line(@cmds[cmd],@snx_name,ost,nil,2)
            end
          end
        end
      end
      jobs.each {|j| j.join}
  end

  def create_dir
    begin
      if not Dir::exists?(@target_dir) then
        FileUtils::mkdir_p(@target_dir)
      end
    rescue Timeout::Error
      write_line(5,@snx_name,@target_dir,nil,1)
    rescue
      write_line(5,@snx_name,@target_dir,nil,2)
    end
  end

  def create_file(ost)
    es=0
    fileName="#{@target_dir}/file.#{ost}"
    if not File::exists?(fileName) then
      system("lfs setstripe -c 1 -i #{ost} #{fileName}")
    end
    cr=`#{$LFS} getstripe -q #{fileName} 2>&1`
    actual_ost=cr.lines[2].split[0]
    if actual_ost.to_i != ost then
      File::unlink(fileName)
      self.write_line(1,@snx_name,ost,nil,3)
      return 0
    end
    self.write_line(1,@snx_name,ost,nil,0)
    return es
  end

  def write(ost)
    fileName="#{@target_dir}/file.#{ost}"
    if not File::exists?(fileName) then
        self.write_line(2,@snx_name,ost,nil,4)
      exit
    end
    output=`dd if=/dev/zero of=#{fileName} bs=4k oflag=direct count=1 2>&1 | tail -1 | awk {'print $6'}`
    duration=(output.to_f() *1000).round
    self.write_line(2,@snx_name,ost,duration,0)
    return 0
  end

  def rm_files
    begin
      FileUtils::rm("#{@target_dir}/file*")
    rescue => e
      self.write_line(3,@snx_name,nil,nil,2)
    end
  end


  def single_touch
    fileName="#{@target_dir}/file.single"
    begin
      f = File.open("#{fileName}")
      pid = f.gets.to_i
      f.close()
      raise() if pid == 0
      Process.kill(0,pid)
      self.write_line(5,@snx_name,nil,nil,9)
      exit
    rescue
      self.single_rm
    begin
      Timeout::timeout(@timeout) {
        start=Time.now
        f = File.open("#{fileName}","w")
        f.write(Process::pid)
        f.close()
        finish=Time.now
        duration=((finish-start)*1000.0).round
        self.write_line(5,@snx_name,0,duration,0)
      }
    rescue Timeout::Error
      self.write_line(5,@snx_name,nil,nil,1)
    rescue =>e
      self.write_line(5,@snx_name,nil,nil,2)
    end
  end
end


  def single_rm
    r=String.new
    begin
      ost=`#{$LFS} getstripe -q  #{@target_dir}/file.single 2>&1`.lines[2].split[0]
      Timeout::timeout(@timeout) {
        start=Time.now
        FileUtils::rm("#{@target_dir}/file.single")
        finish=Time.now
        duration=((finish-start)*1000.0).round
        self.write_line(6,@snx_name,ost,duration,0)
      }
    rescue Timeout::Error
      self.write_line(6,@snx_name,nil,nil,1)
    rescue =>e
      self.write_line(6,@snx_name,nil,nil,2)
    end
  end

  def end
    self.write_line(4,@snx_name,nil,nil,0)
  end
end

md=TEST.new($options[:directory])
if $options[:create] then
  md.para_cmd_osts("create_file")
else
  md.single_touch
  md.para_cmd_osts("write")
  md.single_rm
end
md.end
