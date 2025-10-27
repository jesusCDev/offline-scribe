const fs = require('fs');
const path = require('path');
const { app } = require('electron');

class Logger {
  constructor() {
    this.logDir = null;
    this.logFile = null;
    this.maxLogSize = 10 * 1024 * 1024; // 10 MB
    this.maxLogFiles = 3; // Keep 3 log files
    this.initialized = false;
  }

  /**
   * Initialize the logger
   */
  init() {
    if (this.initialized) return;

    try {
      // Create logs directory in user data
      this.logDir = path.join(app.getPath('userData'), 'logs');
      if (!fs.existsSync(this.logDir)) {
        fs.mkdirSync(this.logDir, { recursive: true });
      }

      // Current log file
      const timestamp = new Date().toISOString().replace(/[:.]/g, '-').split('T')[0];
      this.logFile = path.join(this.logDir, `silent-scribe-${timestamp}.log`);

      this.initialized = true;
      this.info('Logger initialized', { logFile: this.logFile });
    } catch (error) {
      console.error('Failed to initialize logger:', error);
    }
  }

  /**
   * Get log file path
   */
  getLogPath() {
    return this.logFile;
  }

  /**
   * Get logs directory path
   */
  getLogDir() {
    return this.logDir;
  }

  /**
   * Format log entry
   */
  formatLog(level, message, data = null) {
    const timestamp = new Date().toISOString();
    const entry = {
      timestamp,
      level: level.toUpperCase(),
      message,
      ...(data && { data })
    };
    return JSON.stringify(entry);
  }

  /**
   * Write log entry to file
   */
  writeLog(level, message, data = null) {
    if (!this.initialized) {
      this.init();
    }

    try {
      const logEntry = this.formatLog(level, message, data);
      
      // Also log to console
      const consoleMsg = `[${level.toUpperCase()}] ${message}`;
      if (level === 'error') {
        console.error(consoleMsg, data || '');
      } else if (level === 'warn') {
        console.warn(consoleMsg, data || '');
      } else {
        console.log(consoleMsg, data || '');
      }

      // Write to file
      fs.appendFileSync(this.logFile, logEntry + '\n', 'utf8');

      // Check if rotation needed
      this.rotateIfNeeded();
    } catch (error) {
      console.error('Failed to write log:', error);
    }
  }

  /**
   * Rotate logs if file is too large
   */
  rotateIfNeeded() {
    try {
      if (!fs.existsSync(this.logFile)) return;

      const stats = fs.statSync(this.logFile);
      if (stats.size < this.maxLogSize) return;

      // Rotate: rename current to .1, .1 to .2, etc.
      for (let i = this.maxLogFiles - 1; i > 0; i--) {
        const oldFile = `${this.logFile}.${i}`;
        const newFile = `${this.logFile}.${i + 1}`;
        
        if (fs.existsSync(oldFile)) {
          if (i === this.maxLogFiles - 1) {
            // Delete oldest
            fs.unlinkSync(oldFile);
          } else {
            fs.renameSync(oldFile, newFile);
          }
        }
      }

      // Rename current to .1
      fs.renameSync(this.logFile, `${this.logFile}.1`);
    } catch (error) {
      console.error('Failed to rotate logs:', error);
    }
  }

  /**
   * Log levels
   */
  debug(message, data) {
    this.writeLog('debug', message, data);
  }

  info(message, data) {
    this.writeLog('info', message, data);
  }

  warn(message, data) {
    this.writeLog('warn', message, data);
  }

  error(message, data) {
    this.writeLog('error', message, data);
  }

  /**
   * Log Docker operation
   */
  docker(operation, result, data) {
    const level = result.success ? 'info' : 'error';
    this.writeLog(level, `Docker: ${operation}`, {
      success: result.success,
      ...data,
      ...(result.error && { error: result.error })
    });
  }

  /**
   * Read recent log entries
   */
  readRecentLogs(lines = 100) {
    try {
      if (!fs.existsSync(this.logFile)) {
        return [];
      }

      const content = fs.readFileSync(this.logFile, 'utf8');
      const logLines = content.trim().split('\n').filter(l => l);
      
      // Return last N lines
      return logLines.slice(-lines).map(line => {
        try {
          return JSON.parse(line);
        } catch {
          return { raw: line };
        }
      });
    } catch (error) {
      console.error('Failed to read logs:', error);
      return [];
    }
  }
}

// Singleton instance
const logger = new Logger();

module.exports = logger;
