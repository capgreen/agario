import json
from math import sin, cos, sqrt, pi, atan
from random import random

#константы и параметры
FOOD_MASS = None
GAME_HEIGHT = None
GAME_TICKS = None
GAME_WIDTH = None
INERTION_FACTOR = None
MAX_FRAGS_CNT = None
SPEED_FACTOR = None
TICKS_TIL_FUSION = None
VIRUS_RADIUS = None
VIRUS_SPLIT_MASS = None
VISCOSITY = None
FOOD_RADIUS = 2.5
SPLIT_THRESHOLD = 120
 
SCORE_FOOD = 1
SCORE_ENEMY_PART = 10
SCORE_ENEMY = 100
SCORE_VIRUS_BURST = 2
CORNERS = []

def initParams( data ):
    global FOOD_MASS, GAME_HEIGHT, GAME_TICKS, GAME_WIDTH, INERTION_FACTOR, MAX_FRAGS_CNT, \
                SPEED_FACTOR, TICKS_TIL_FUSION, VIRUS_RADIUS, VIRUS_SPLIT_MASS, VISCOSITY
    FOOD_MASS = data.get( 'FOOD_MASS' )
    GAME_HEIGHT = data.get( 'GAME_HEIGHT' )
    GAME_TICKS = data.get( 'GAME_TICKS' )
    GAME_WIDTH = data.get( 'GAME_WIDTH' )
    INERTION_FACTOR = data.get( 'INERTION_FACTOR' )
    MAX_FRAGS_CNT = data.get( 'MAX_FRAGS_CNT' )
    SPEED_FACTOR = data.get( 'SPEED_FACTOR' )
    TICKS_TIL_FUSION = data.get( 'TICKS_TIL_FUSION' )
    VIRUS_RADIUS = data.get( 'VIRUS_RADIUS' )
    VIRUS_SPLIT_MASS = data.get( 'VIRUS_SPLIT_MASS' )
    VISCOSITY = data.get( 'VISCOSITY' )
    CORNERS.append( GameObject( { 'X': 0, 'Y': 0 } ) )
    CORNERS.append( GameObject( { 'X': GAME_WIDTH, 'Y': 0 } ) )
    CORNERS.append( GameObject( { 'X': GAME_WIDTH, 'Y': GAME_HEIGHT } ) )
    CORNERS.append( GameObject( { 'X': 0, 'Y': GAME_HEIGHT } ) )

def makeCommand( x, y, debug ):
        command = {}
        command['X'] = x
        command['Y'] = y
        command['Debug'] = debug
        return command;
    
def distance( a, b ):
    return sqrt( ( a.X - b.X ) ** 2 + ( a.Y - b.Y ) ** 2 )

def normalize( x, y ):
    l = sqrt( x ** 2 + y ** 2 )
    if l == 0:
        return x, y
    else:
        return x / l, y / l

class GameObject:
    def __init__( self, data ):
        self.X = data.get( 'X' )
        self.Y = data.get( 'Y' )
    
    def distance( self, other ):
        return distance( self, other )
    
class Virus( GameObject ):
    def __init__( self, data ):
        super().__init__( data )
        self.Id = data.get( 'Id' )
        self.M = data.get( 'M' )
    
class PlayerPart( Virus ):
    def __init__( self, data ):
        super().__init__( data )
        self.R = data.get( 'R' )
    
    # максимальная скорость игрока
    def maxSpeed( self ):
        return SPEED_FACTOR / sqrt( self.M )    
        
class MinePart( PlayerPart ):
    def __init__( self, data ):
        super().__init__( data )
        self.VX = data.get( 'SX' )
        self.VY = data.get( 'SY' )
        self.V = sqrt( self.VX ** 2 + self.VY ** 2 )
        self.vx, self.vy = normalize( self.VX, self.VY )
        # таймер слияния - может отсутствовать
        if 'TTF' in data:
            self.TTF = data.get( 'TTF' ) 
        else:
            self.TTF = 0
        self.MaxSpeed = self.maxSpeed()
        self.Speed = sqrt( self.VX ** 2 + self.VY ** 2 )
        
    def distanceToBorder( self ):
        return min( [self.X, GAME_WIDTH - self.X, self.Y, GAME_HEIGHT - self.Y ] )
    
    def borderStandoff( self ):
        minDistance = self.R + 50.0
        nx = 0.0
        ny = 0.0
        if self.X < minDistance:
            nx = 1.0 / ( 2 + self.X )
        elif self.X > GAME_WIDTH - minDistance:
            nx = -1.0 / ( 2 + GAME_WIDTH - self.X )
        if self.Y < minDistance:
            ny = 1.0 / ( 2 + self.Y )
        elif self.Y > GAME_HEIGHT - minDistance:
            ny = -1.0 / ( 2 + GAME_HEIGHT - self.Y )
        if nx != 0 or ny != 0:
            nx, ny = normalize( nx, ny )
        return nx, ny
    
    # оценка времени достижения заданного объекта с перекрытием его на 2/3 его диаметра
    def getTimeToTarget( self, target ):
        captureDistance = self.R - target.R
        T = 0
        X0 = self.X
        Y0 = self.Y
        Vx0 = self.VX
        Vy0 = self.VY
        curDistance = sqrt( (self.X - target.X)**2 + (self.Y - target.Y)**2 )
        prevDistance = curDistance
        while curDistance > captureDistance and T < 100:
            X0, Y0, Vx0, Vy0, curDistance = self.stepToTarget( X0, Y0, Vx0, Vy0, target.X, target.Y )
            if prevDistance < curDistance:
                return 100
            prevDistance = curDistance
            T += 1
        return T
        
    def stepToTarget( self, X0, Y0, Vx0, Vy0, Xt, Yt ):
        t = self.getBestDirectionToTarget( X0, Y0, Vx0, Vy0, Xt, Yt )
        Vmax = self.MaxSpeed
        a = INERTION_FACTOR / self.M
        Vx1 = (1 - a)*Vx0 + a * Vmax * cos(t)
        Vy1 = (1 - a)*Vy0 + a * Vmax * sin(t)
        X1 = X0 + Vx1
        Y1 = Y0 + Vy1
        return X1, Y1, Vx1, Vy1, sqrt( (X1 - Xt)**2 + (Y1 - Yt)**2  )
    
    # направление приложения силы для максимального приближения к цели
    def getBestDirectionToTarget( self, X0, Y0, Vx0, Vy0, Xt, Yt ):
        # координаты цели относительно нас
        X = Xt - X0
        Y = Yt - Y0
        Vx = Vx0
        Vy = Vy0
        V = sqrt( Vx ** 2 + Vy ** 2 )
        L = sqrt( X ** 2 + Y ** 2 )
        a = INERTION_FACTOR / self.M
        Vmax = SPEED_FACTOR / sqrt( self.M )
        # экстремальные углы
        k1 = sqrt( (a - 1)**2 * V * V + 2 * ( a - 1 ) * ( X * Vx + Y * Vy ) + L ** 2 )
        k2 = (1 - a) * Vx - X
        k3 = Y - (1 - a) * Vy
        t1 = 2 * atan( ( k1 + k2 ) / k3 )
        t2 = -2 * atan( ( k1 - k2 ) / k3 )
        # результаты для первого угла
        X1 = (1 - a)*Vx + a * Vmax * cos(t1)
        Y1 = (1 - a)*Vy + a * Vmax * sin(t1)
        L1 = sqrt( ( X - X1 ) ** 2 + ( Y - Y1 ) ** 2 )
        # результаты для второго угла
        X2 = (1 - a)*Vx + a * Vmax * cos(t2)
        Y2 = (1 - a)*Vy + a * Vmax * sin(t2)
        L2 = sqrt( ( X - X2 ) ** 2 + ( Y - Y2 ) ** 2 )
        tmin = t1 # угол приложения силы, который приведет к максимальному приближению к цели
        if L1 > L2:
            tmin = t2
        return tmin
            
class Food( GameObject ):
    def __init__( self, data ):
        super().__init__( data )
        self.R = FOOD_RADIUS

class Ejection( GameObject ):
    def __init__( self, data ):
        super().__init__( data )
        self.pId = data.get( 'pId' )
    
class Strategy:
    
    def __init__( self ):
        self.mine = []
        self.direction = None
        self.food = []
        self.ejection = []
        self.virus = []
        self.player = []
        self.dangerous = []
        self.eatable = []
        self.fieldDiameter = None
        self.minSelfRadius = None
        self.left = None
        self.right = None
        self.top = None
        self.bottom = None
        self.isSplittable = False
        self.runPoint = None #точка отступление
        self.totalMass = 0
        self.timeFromLastContact = 1000 #время с момента последнего наблюдения противника
        self.corners = [] # углы карты - не рекомендуется убегать в угол
    
        
    def parseData( self, data ):
        mine, objects = data.get( 'Mine' ), data.get( 'Objects' )
        self.mine.clear()
        self.minSelfRadius = sqrt( GAME_HEIGHT ** 2 + GAME_WIDTH ** 2 );
        self.left = GAME_WIDTH
        self.right = 0
        self.top = GAME_HEIGHT
        self.bottom = 0
        self.isSplittable = False
        minMass = 10000.0
        self.totalMass = 0
        for m in mine:
            self.mine.append( MinePart( m ) )
        for m in self.mine:
            self.minSelfRadius = min( self.minSelfRadius, m.R )
            self.left = min( self.left, m.X - m.R )
            self.right = max( self.right, m.X + m.R )
            self.top = min( self.top, m.Y - m.R )
            self.bottom = max( self.bottom, m.Y + m.R )
            if m.M >= SPLIT_THRESHOLD:
                self.isSplittable = True
            if m.M < minMass:
                minMass = m.M
            self.totalMass += m.M
        self.food.clear()
        self.ejection.clear()
        self.virus.clear()
        self.player.clear()
        self.dangerous.clear()
        self.eatable.clear()
        for o in objects:
            objectType = o.get( 'T' )
            if objectType == 'F':
                self.food.append( Food( o ) )
            elif objectType == 'E':
                self.ejection.append( Ejection( o ) )
            elif objectType == 'V':
                self.virus.append( Virus( o ) )
            elif objectType == 'P':
                p = PlayerPart( o )
                if minMass * 1.2 < p.M:
                    self.dangerous.append( p )
                elif minMass > p.M * 1.2:
                    self.eatable.append( p )
                else:
                    self.player.append( p )
        if len( self.dangerous ) > 0 or len( self.eatable ) > 0 or len( self.player ) > 0:
            self.timeFromLastContact = 0
        else:
            self.timeFromLastContact += 1
            
    def run( self ):
        initParams( json.loads( input() ) )
        self.fieldDiameter = sqrt( GAME_WIDTH ** 2 + GAME_HEIGHT ** 2 )
        while True:
            data = json.loads( input() )
            cmd = self.on_tick( data )
            print( json.dumps(cmd) )

    def isFoodReachable( self, food ):
        effectiveRadius = self.minSelfRadius - FOOD_RADIUS / 6
        # для угла (0, 0)
        if food.X < self.minSelfRadius and food.Y < self.minSelfRadius:
            checkPoint = GameObject( { 'X': self.minSelfRadius, 'Y': self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X > GAME_WIDTH - self.minSelfRadius and food.Y < self.minSelfRadius:
            checkPoint = GameObject( { 'X': GAME_WIDTH - self.minSelfRadius, 'Y': self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X < self.minSelfRadius and food.Y > GAME_HEIGHT - self.minSelfRadius:
            checkPoint = GameObject( { 'X': self.minSelfRadius, 'Y': GAME_HEIGHT - self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        elif food.X > GAME_WIDTH - self.minSelfRadius and food.Y > GAME_HEIGHT - self.minSelfRadius:
            checkPoint = GameObject( { 'X': GAME_WIDTH - self.minSelfRadius, 'Y': GAME_HEIGHT - self.minSelfRadius } )
            return distance( checkPoint, food ) < effectiveRadius
        else:
            return food.X > ( FOOD_RADIUS / 6 ) and food.X < ( GAME_WIDTH - FOOD_RADIUS / 6 ) and food.Y > ( FOOD_RADIUS / 6 ) and food.Y < ( GAME_HEIGHT - FOOD_RADIUS / 6 )
        
    def getNearestFood( self ):
        nearest = None
        minDist = self.fieldDiameter
        for food in self.food:
            if not self.isFoodReachable( food ):
                continue
            for m in self.mine:
                dist = m.distance( food )
                if dist < minDist:
                    minDist = dist
                    nearest = food
        return nearest
    
    # ищем минимальное расстояние между своими частями и заданным объектом
    def distance( self, obj ):
        return min( map( (lambda x: x.distance( obj ) ), self.mine ) )
            
    # ищем единичный вектор отталкивания от границ
    # от границ отталкиваемся по нормали 
    def getBorderStandoff( self ):
        dx = 0
        dy = 0
        dMin = 1000000
        for m in self.mine:
            d = m.distanceToBorder()
            if d < dMin:
                dx, dy = m.borderStandoff()
                dMin = d
        return dx, dy
    
    # ищем пару опасный противник - своя часть с минимальным расстоянием
    # убегать будем по направлени, соединяющему центры этой пары
    def getRunPoint( self ):
        minDistance = 10000
        mineEnd = None
        enemyEnd = None
        for mine in self.mine:
            for enemy in self.dangerous:
                distance = mine.distance( enemy )
                if minDistance > distance:
                    mineEnd = mine
                    enemyEnd = enemy
                    minDistance = distance
        dx = mineEnd.X - enemyEnd.X
        dy = mineEnd.Y - enemyEnd.Y
        # единичный вектор от противника к нам
        dx, dy = normalize( dx, dy )
        # вектор отталкивания от границ
        sx, sy = self.getBorderStandoff()
        dx += sx
        dy += sy
        dx, dy = normalize( dx, dy )
        x, y = self.setPointOnBorder( self.mine[0], dx, dy )
        return GameObject( { 'X': x, 'Y': y } )
    
    def getAttackPoint( self ):
        minDistance = 10000
        mineEnd = None
        enemyEnd = None
        for mine in self.mine:
            for enemy in self.eatable:
                distance = mine.distance( enemy )
                if minDistance > distance:
                    mineEnd = mine
                    enemyEnd = enemy
                    minDistance = distance
        dx = enemyEnd.X - mineEnd.X
        dy = enemyEnd.Y - mineEnd.Y
        d = sqrt( dx ** 2 + dy ** 2 )
        x = mineEnd.X + ( dx * 100.0 / d )
        y = mineEnd.Y + ( dy * 100.0 / d )
        return GameObject( { 'X': x, 'Y': y } )
    
    def currentSpeed( self ):
        VX = 0
        VY = 0
        for m in self.mine:
            VX += m.VX * m.M
            VY += m.VY * m.M
        VX /= self.totalMass
        VY /= self.totalMass
        return VX, VY
    
    def setPointOnBorder( self, pt, nx, ny ):
        # ищем границу, которую пересекаем раньше всего
        x = pt.X
        y = pt.Y
        Lmin = 10000
        l = []
        if nx != 0:
            l.append( -x/nx )
            l.append( (GAME_WIDTH - x)/nx )
        if ny != 0:
            l.append( -y/ny )
            l.append( (GAME_HEIGHT-y)/ny )
        l.sort()
        for curLen in l:
            if curLen > 0 and curLen < Lmin:
                Lmin = curLen
        return x + nx * Lmin, y + ny * Lmin
    
    def moveToFood( self ):
        minTime = GAME_TICKS
        bestFood = None
        bestMine = None
        for m in self.mine:
            for f in self.food:
                t = m.getTimeToTarget( f )
                if t < minTime:
                    bestMine = m
                    bestFood = f
                    minTime = t
        if minTime >= 100:
            return self.moveFree()
        t = bestMine.getBestDirectionToTarget( bestMine.X, bestMine.Y, bestMine.VX, bestMine.VY, bestFood.X, bestFood.Y )
        nx = cos(t)
        ny = sin(t)
        x, y = self.setPointOnBorder( bestMine, nx, ny )
        return makeCommand( x, y, 'to food' )
    
    def moveFree( self ):
        # движемся в заданном напралении
        # в свободном состоянии движемся по напралению скорости, если она есть
        VX, VY = self.currentSpeed()
        if VX == 0 and VY == 0:
            angle = 2 * pi * random()
            VX = cos( angle )
            VY = sin( angle )
        VX, VY = normalize( VX, VY )
        dx, dy = self.getBorderStandoff()
        if dx != 0 or dy != 0:
            VX += dx
            VY += dy
            VX, VY = normalize( VX, VY )
        x, y = self.setPointOnBorder( self.mine[0], VX, VY )
        return makeCommand( x, y, 'by direction' )
    
    def on_tick( self, data ):
        self.parseData( data )
        command = {}
        if len( self.mine ) == 0:
            command = makeCommand( 0, 0, 'game over' )
        else:
            if len( self.dangerous ) > 0:
                 #избегаем опасных соседей
                 self.runPoint = self.getRunPoint()
                 command = makeCommand( self.runPoint.X, self.runPoint.Y, 'run' )
            elif len( self.eatable ) > 0:
                 #пытаемся съесть конкурента если можем
                 attackPoint = self.getAttackPoint()
                 command = makeCommand( attackPoint.X, attackPoint.Y, 'run' )
            else:
                if len( self.food ) > 0:
                    # пытаемся съесть еду если видно
                    command = self.moveToFood()
                else:
                    command = self.moveFree()
                if self.isSplittable and self.timeFromLastContact > 50:
                    command['Split'] = True
        # нужно скорректировать для случая близости к границе
        return command

if __name__ == '__main__':
    s = Strategy()
    s.run()